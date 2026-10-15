// SPDX-License-Identifier: MIT
import Foundation
import GSIPStorageCore

final class Trace {
    var events: [String] = []
}

final class MemoryAnchor: StorageAnchor {
    var value: AnchorState?
    var failRead = false
    var failPending = false
    var failClean = false
    var failPendingAfterWrite = false
    var pendingDelay: TimeInterval = 0
    var observedMainThread = false
    let trace: Trace
    private var nonceCount = 0
    init(_ value: AnchorState?, trace: Trace) { self.value = value; self.trace = trace }
    func read() throws -> AnchorState? {
        observedMainThread = observedMainThread || Thread.isMainThread
        trace.events.append("anchor-read")
        if failRead { throw StorageHold.unavailable }
        return value
    }
    func update(_ state: AnchorState, expecting: AnchorState) throws {
        trace.events.append(state.phase == .pending ? "anchor-pending" : "anchor-clean")
        if state.phase == .pending && failPending || state.phase == .clean && failClean {
            throw StorageHold.unavailable
        }
        guard value == expecting else { throw StorageHold.anchorMismatch }
        value = state
        if state.phase == .pending && pendingDelay > 0 { Thread.sleep(forTimeInterval: pendingDelay) }
        if state.phase == .pending && failPendingAfterWrite { throw StorageHold.unavailable }
    }
    func freshNonce() throws -> String { nonceCount += 1; return "nonce-\(nonceCount)" }
}

final class MemoryDatabase: StorageDatabase {
    var state: DatabaseSnapshot
    var receipts: [String: OperationReceipt] = [:]
    var records: [String: StorageRecord] = [:]
    var failBoundary = false
    var failPostBoundary = false
    var failCommit = false
    var commitError: StorageHold = .interrupted
    var commitCount = 0
    var receiptDelay: TimeInterval = 0
    let trace: Trace
    init(state: DatabaseSnapshot, trace: Trace) { self.state = state; self.trace = trace }
    func validateBoundary() throws {
        trace.events.append("boundary")
        if failBoundary || (failPostBoundary && commitCount > 0) { throw StorageHold.boundary }
    }
    func snapshot() throws -> DatabaseSnapshot { trace.events.append("snapshot"); return state }
    func digest(_ request: StorageRequest) throws -> String {
        // Deliberately injected, noncryptographic double. The real SQLite adapter uses SHA256.
        let encoder = JSONEncoder(); encoder.outputFormatting = .sortedKeys
        let bytes = try encoder.encode(request)
        var value: UInt64 = 1469598103934665603
        for byte in bytes { value = (value ^ UInt64(byte)) &* 1099511628211 }
        let part = String(format: "%016llx", value)
        return String(repeating: part, count: 4)
    }
    func receipt(operationID: String) throws -> OperationReceipt? {
        if receiptDelay > 0 { Thread.sleep(forTimeInterval: receiptDelay) }
        return receipts[operationID]
    }
    func prepare(_ request: StorageRequest) throws {
        switch request.mutation {
        case let .put(store, key, _, expected):
            let current = records[store.rawValue + key]?.revision ?? 0
            guard current == expected else { throw StorageHold.revisionMismatch }
            guard current < StorageLimits.maxCounter else { throw StorageHold.exhausted }
        case let .remove(store, key, expected):
            guard records[store.rawValue + key]?.revision == expected else { throw StorageHold.revisionMismatch }
        case .clear: break
        default: throw StorageHold.invalidRequest
        }
    }
    func commit(_ request: StorageRequest, next: DatabaseSnapshot, digest: String) throws -> OperationReceipt {
        trace.events.append("db-commit")
        if failCommit { throw commitError }
        var revision: UInt64 = 0
        switch request.mutation {
        case let .put(store, key, bytes, expected):
            let current = records[store.rawValue + key]?.revision ?? 0
            guard current == expected else { throw StorageHold.revisionMismatch }
            guard current < StorageLimits.maxCounter else { throw StorageHold.exhausted }
            revision = next.revision
            records[store.rawValue + key] = StorageRecord(bytes: bytes, revision: revision)
        case let .remove(store, key, expected):
            guard records[store.rawValue + key]?.revision == expected else { throw StorageHold.revisionMismatch }
            records.removeValue(forKey: store.rawValue + key)
        case .clear: records.removeAll()
        default: throw StorageHold.invalidRequest
        }
        let acknowledgement = StorageAcknowledgement(operationID: request.operationID, revision: next.revision,
                                                       generation: next.generation, recordRevision: revision)
        let receipt = OperationReceipt(requestDigest: digest, lease: request.lease,
                                       commitNonce: next.commitNonce, acknowledgement: acknowledgement, kind: request.mutation.kind)
        state = next; receipts[request.operationID] = receipt; commitCount += 1
        return receipt
    }
    func read(store: LogicalStore, key: String) throws -> StorageRecord? { records[store.rawValue + key] }
}

func syntheticSnapshot(revision: UInt64 = 0, generation: UInt64 = 0, nonce: String = "initial") -> DatabaseSnapshot {
    DatabaseSnapshot(installation: "synthetic-install", owner: "synthetic-owner", authEpoch: 0,
                     revision: revision, generation: generation, commitNonce: nonce)
}
func syntheticLease(generation: UInt64 = 0, launch: String = "synthetic-launch") -> StorageLease {
    StorageLease(owner: "synthetic-owner", authEpoch: 0, launch: launch, generation: generation)
}
func syntheticPut(_ operation: String = "operation-one", bytes: Data = Data([1]), lease: StorageLease = syntheticLease(), revision: UInt64 = 0) -> StorageRequest {
    StorageRequest(operationID: operation, lease: lease, mutation: .put(store: .submissions, key: "synthetic-canary", bytes: bytes, expectedRevision: revision))
}
func requiredSimulatorAuthority() throws -> SyntheticFixtureAuthority {
    let expected = ProcessInfo.processInfo.environment["GSIP_PROTOTYPE_EXPECTED_BUNDLE_ID"] ?? Bundle.main.bundleIdentifier ?? ""
    return try SyntheticFixtureAuthority.forOwnedSimulator(expectedBundleIdentifier: expected)
}
