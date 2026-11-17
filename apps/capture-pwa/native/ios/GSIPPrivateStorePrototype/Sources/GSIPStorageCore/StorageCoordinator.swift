// SPDX-License-Identifier: MIT
import Foundation
import Dispatch

private final class NativeCompletion<Value> {
    private let lock = NSLock()
    private var value: Value?
    func set(_ value: Value) { lock.lock(); defer { lock.unlock() }; self.value = value }
    func get() -> Value? { lock.lock(); defer { lock.unlock() }; return value }
}

/// The only app-facing writer. Calls are serialized off the UI thread; timeouts permanently
/// revoke this coordinator. No transaction crosses a JavaScript, user or network callback.
public final class StorageCoordinator {
    private let database: StorageDatabase
    private let anchor: StorageAnchor
    private let executor = DispatchQueue(label: "gsip.synthetic-storage.coordinator")
    private var active: StorageLease?
    private var stopped = false
    private let writerGranted: Bool
    private let timeoutMilliseconds: Int
    private let lifecycleLock = NSLock()
    private var revocation: StorageHold?
    public convenience init(database: StorageDatabase, anchor: StorageAnchor) {
        self.init(database: database, anchor: anchor, timeoutMilliseconds: 5_000)
    }
    init(database: StorageDatabase, anchor: StorageAnchor, timeoutMilliseconds: Int) {
        self.database = database; self.anchor = anchor
        self.timeoutMilliseconds = max(1, min(timeoutMilliseconds, 5_000))
        self.writerGranted = (database as? ExcludedSQLiteStore)?.claimWriter() ?? true
    }
    deinit { if writerGranted { (database as? ExcludedSQLiteStore)?.releaseWriter() } }

    public func admit(lease: StorageLease) -> StorageAdmission {
        if let reason = revoked() { return .held(reason) }
        return perform(fallback: .held(.interrupted)) { [self] in
            if let reason = revoked() { return .held(reason) }
            guard writerGranted else { return .held(.busy) }
            guard !stopped else { return .held(.suspended) }
            guard lease.isValid else { return .held(.invalidRequest) }
            if let active, active != lease { return .held(.staleLease) }
            active = nil
            do {
                try database.validateBoundary()
                let snapshot = try checkedSnapshot()
                guard snapshot.owner == lease.owner else { return .held(.ownerMismatch) }
                guard snapshot.authEpoch == lease.authEpoch else { return .held(.staleLease) }
                guard snapshot.generation == lease.generation else { return .held(.generationMismatch) }
                guard let observed = try anchor.read() else { return .held(.missingAnchor) }
                guard observed.isValid else { return .held(.anchorPolicy) }
                if observed.phase == .pending {
                    guard observed.installation == snapshot.installation else { return .held(.anchorMismatch) }
                    if snapshot.revision == observed.revision { return .held(.pendingOldDatabase) }
                    guard observed.nextRevision == snapshot.revision, observed.commitNonce == snapshot.commitNonce,
                          let operationID = observed.operationID, let digest = observed.operationDigest else {
                        return .held(.anchorMismatch)
                    }
                    guard let receipt = try database.receipt(operationID: operationID),
                          receipt.requestDigest == digest, receipt.kind == observed.operationKind, receipt.commitNonce == snapshot.commitNonce,
                          receipt.acknowledgement.operationID == operationID,
                          receipt.acknowledgement.revision == snapshot.revision,
                          receipt.acknowledgement.generation == snapshot.generation,
                          receipt.lease.owner == snapshot.owner,
                          receipt.lease.authEpoch == snapshot.authEpoch,
                          (receipt.kind == "clear" ? (snapshot.generation > 0 && receipt.lease.generation == snapshot.generation - 1) : receipt.lease.generation == snapshot.generation)
                    else { return .held(.unknownReceipt) }
                    let clean = AnchorState.clean(snapshot)
                    if let reason = revoked() { throw reason }
                    try anchor.update(clean, expecting: observed)
                    guard try anchor.read() == clean else { return .held(.anchorMismatch) }
                } else {
                    guard observed == .clean(snapshot) else { return .held(.anchorMismatch) }
                }
                try database.validateBoundary()
                if let reason = revoked() { return .held(reason) }
                active = lease
                return .admitted(lease)
            } catch { active = nil; return .held(hold(error)) }
        }
    }

    public func isCurrent(_ lease: StorageLease) -> Bool {
        guard revoked() == nil else { return false }
        return perform(fallback: false) { [self] in !stopped && revoked() == nil && active == lease }
    }
    public func suspend() {
        revoke(.suspended)
        executor.async { [self] in stopped = true; active = nil }
    }
    private func revoked() -> StorageHold? {
        lifecycleLock.lock(); defer { lifecycleLock.unlock() }; return revocation
    }
    private func revoke(_ reason: StorageHold) {
        lifecycleLock.lock(); defer { lifecycleLock.unlock() }
        if revocation == nil { revocation = reason }
    }
    private func perform<Value>(fallback: Value, _ body: @escaping () -> Value) -> Value {
        guard revoked() == nil else { return fallback }
        let completion = NativeCompletion<Value>()
        let finished = DispatchSemaphore(value: 0)
        executor.async { [self] in
            completion.set(revoked() == nil ? body() : fallback)
            finished.signal()
        }
        guard finished.wait(timeout: .now() + .milliseconds(timeoutMilliseconds)) == .success else {
            revoke(.interrupted); return fallback
        }
        guard revoked() == nil else { return fallback }
        return completion.get() ?? fallback
    }

    public func read(store: LogicalStore, key: String, lease: StorageLease) -> StorageReadResult {
        if let reason = revoked() { return .held(reason) }
        return perform(fallback: .held(.interrupted)) { [self] in
            if let reason = revoked() { return .held(reason) }
            guard !stopped else { return .held(.suspended) }
            guard active == lease else { return .held(.staleLease) }
            guard store.isPayload, StorageLimits.validIdentifier(key) else { return .held(.invalidRequest) }
            do {
                try database.validateBoundary()
                let snapshot = try checkedSnapshot()
                guard snapshot.owner == lease.owner, snapshot.authEpoch == lease.authEpoch,
                      snapshot.generation == lease.generation else { active = nil; return .held(.staleLease) }
                guard try anchor.read() == .clean(snapshot) else { active = nil; return .held(.anchorMismatch) }
                let record = try database.read(store: store, key: key)
                guard record?.bytes.count ?? 0 <= StorageLimits.chunkBytes else { return .held(.quota) }
                try database.validateBoundary()
                if let reason = revoked() { active = nil; return .held(reason) }
                return record.map(StorageReadResult.found) ?? .absent
            } catch { active = nil; return .held(hold(error)) }
        }
    }

    public func execute(_ request: StorageRequest) -> StorageResult {
        if let reason = revoked() { return .held(reason) }
        return perform(fallback: .held(.interrupted)) { [self] in
            if let reason = revoked() { return .held(reason) }
            guard !stopped else { return .held(.suspended) }
            guard request.isValid else { return .held(.invalidRequest) }
            guard let admitted = active else { return .held(.staleLease) }
            let retryingClear: Bool
            if case .clear = request.mutation {
                retryingClear = admitted.owner == request.lease.owner && admitted.authEpoch == request.lease.authEpoch &&
                    admitted.launch == request.lease.launch && admitted.generation > 0 &&
                    request.lease.generation == admitted.generation - 1
            } else { retryingClear = false }
            guard admitted == request.lease || retryingClear else { return .held(.staleLease) }
            var beganPending = false
            do {
                try database.validateBoundary()
                let current = try checkedSnapshot()
                guard current.owner == admitted.owner, current.authEpoch == admitted.authEpoch,
                      current.generation == admitted.generation else { active = nil; return .held(.staleLease) }
                let clean = AnchorState.clean(current)
                guard try anchor.read() == clean else { active = nil; return .held(.anchorMismatch) }
                let digest = try database.digest(request)
                if let receipt = try database.receipt(operationID: request.operationID) {
                    guard receipt.requestDigest == digest, receipt.kind == request.mutation.kind, receipt.lease == request.lease,
                          receipt.acknowledgement.revision <= current.revision,
                          receipt.acknowledgement.generation == current.generation else { return .held(.operationConflict) }
                    try database.validateBoundary()
                    if let reason = revoked() { active = nil; return .held(reason) }
                    let old = receipt.acknowledgement
                    let retry = StorageAcknowledgement(operationID: old.operationID, revision: old.revision,
                                                       generation: old.generation, recordRevision: old.recordRevision, retry: true)
                    return result(request, retry)
                }
                guard !retryingClear else { return .held(.staleLease) }
                guard current.revision < StorageLimits.maxCounter else { return .held(.exhausted) }
                let generation: UInt64
                if case .clear = request.mutation {
                    guard current.generation < StorageLimits.maxCounter else { return .held(.exhausted) }
                    generation = current.generation + 1
                } else { generation = current.generation }
                try database.prepare(request)
                let nonce = try anchor.freshNonce()
                guard StorageLimits.validIdentifier(nonce), nonce != current.commitNonce else { return .held(.anchorPolicy) }
                let next = DatabaseSnapshot(installation: current.installation, owner: current.owner,
                                            authEpoch: current.authEpoch, revision: current.revision + 1,
                                            generation: generation, commitNonce: nonce)
                let pending = AnchorState(phase: .pending, installation: current.installation,
                                          revision: current.revision, nextRevision: next.revision, commitNonce: nonce,
                                          operationID: request.operationID, operationDigest: digest, operationKind: request.mutation.kind)
                if let reason = revoked() { throw reason }
                beganPending = true
                try anchor.update(pending, expecting: clean)
                guard try anchor.read() == pending else { throw StorageHold.anchorMismatch }
                if let reason = revoked() { throw reason }
                let receipt = try database.commit(request, next: next, digest: digest)
                guard try database.snapshot() == next,
                      receipt.requestDigest == digest, receipt.kind == request.mutation.kind, receipt.commitNonce == nonce,
                      receipt.lease == request.lease, receipt.acknowledgement.operationID == request.operationID,
                      receipt.acknowledgement.revision == next.revision,
                      receipt.acknowledgement.generation == next.generation else { throw StorageHold.unknownReceipt }
                if let reason = revoked() { throw reason }
                let final = AnchorState.clean(next)
                try anchor.update(final, expecting: pending)
                guard try anchor.read() == final else { throw StorageHold.anchorMismatch }
                try database.validateBoundary()
                guard active == request.lease, !stopped, revoked() == nil else { throw StorageHold.staleLease }
                if case .clear = request.mutation {
                    active = StorageLease(owner: request.lease.owner, authEpoch: request.lease.authEpoch,
                                          launch: request.lease.launch, generation: next.generation)
                }
                return result(request, receipt.acknowledgement)
            } catch {
                let outcome = hold(error)
                let validationOnly: [StorageHold] = [.invalidRequest, .revisionMismatch, .quota, .exhausted, .operationConflict, .staleLease]
                if beganPending || !validationOnly.contains(outcome) { active = nil }
                return .held(outcome)
            }
        }
    }

    private func checkedSnapshot() throws -> DatabaseSnapshot {
        let snapshot = try database.snapshot()
        guard snapshot.schema == 1 else { throw StorageHold.unknownSchema }
        guard snapshot.isValid else { throw StorageHold.corrupt }
        return snapshot
    }
    private func result(_ request: StorageRequest, _ acknowledgement: StorageAcknowledgement) -> StorageResult {
        switch request.mutation {
        case .beginStage, .appendStage: return .staged(acknowledgement)
        default: return .acknowledged(acknowledgement)
        }
    }
    private func hold(_ error: Error) -> StorageHold { (error as? StorageHold) ?? .unavailable }

    /// Harness-only seeding; this is never ordinary app initialization or bridge callable.
    public static func syntheticFixture(authority: SyntheticFixtureAuthority, owner: String,
                                        protectedDataAvailable: @escaping () -> Bool = { false }) throws ->
        (coordinator: StorageCoordinator, lease: StorageLease, identity: SyntheticRunIdentity) {
        let identity = try KeychainAnchor.makeRunIdentity(authority: authority)
        let database = try ExcludedSQLiteStore.createSyntheticFixture(authority: authority, identity: identity, owner: owner, protectedDataAvailable: protectedDataAvailable)
        let anchor = KeychainAnchor(authority: authority, identity: identity)
        let coordinator = StorageCoordinator(database: database, anchor: anchor)
        let seedFailure: StorageHold? = coordinator.perform(fallback: StorageHold.interrupted) {
            do { try anchor.seedSyntheticFixture(.clean(database.snapshot())); return nil }
            catch { return (error as? StorageHold) ?? .unavailable }
        }
        if let seedFailure { throw seedFailure }
        let lease = StorageLease(owner: owner, authEpoch: 0, launch: try anchor.freshNonce(), generation: 0)
        guard coordinator.admit(lease: lease) == .admitted(lease) else { throw StorageHold.anchorMismatch }
        return (coordinator, lease, identity)
    }
}
