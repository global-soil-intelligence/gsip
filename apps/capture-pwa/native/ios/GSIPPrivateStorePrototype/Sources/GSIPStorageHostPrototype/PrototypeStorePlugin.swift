// SPDX-License-Identifier: MIT
import Foundation
import Capacitor
import GSIPStorageCore

/// Native-only binding. JavaScript cannot supply or replace any authority field.
final class PrototypeStorageSession {
    let coordinator: StorageCoordinator
    private let lock = NSLock()
    private var boundLease: StorageLease
    private let hostIsActive: () -> Bool
    private var revoked = false
    private struct Permit {
        let lease: StorageLease
        let request: PrototypeWireRequest
        let issued: TimeInterval
    }
    private var permits: [String: Permit] = [:]
    private var seenCallbacks: Set<String> = []
    private var activeCallback: String?

    init(coordinator: StorageCoordinator, lease: StorageLease, hostIsActive: @escaping () -> Bool) {
        self.coordinator = coordinator
        self.boundLease = lease
        self.hostIsActive = hostIsActive
    }

    var lease: StorageLease {
        lock.lock(); defer { lock.unlock() }
        return boundLease
    }

    var isCurrent: Bool {
        lock.lock()
        let candidate = boundLease
        let allowed = !revoked
        lock.unlock()
        guard allowed, hostIsActive(), coordinator.isCurrent(candidate) else { return false }
        lock.lock(); defer { lock.unlock() }
        return !revoked && boundLease == candidate
    }

    func revoke() {
        lock.lock(); defer { lock.unlock() }
        revoked = true
        permits.removeAll()
        activeCallback = nil
    }

    /// Capture native authority at message receipt, before upstream queues its plugin call.
    func register(callback: String, request: PrototypeWireRequest) -> Bool {
        guard StorageLimits.validIdentifier(callback), callback.utf8.count <= 64, isCurrent else { return false }
        let captured = lease
        lock.lock(); defer { lock.unlock() }
        guard !revoked, boundLease == captured, seenCallbacks.count < 256,
              activeCallback == nil, permits.isEmpty, !seenCallbacks.contains(callback) else { return false }
        activeCallback = callback
        seenCallbacks.insert(callback)
        permits[callback] = Permit(lease: captured, request: request, issued: ProcessInfo.processInfo.systemUptime)
        return true
    }

    func consume(callback: String, request: PrototypeWireRequest) -> StorageLease? {
        lock.lock()
        let permit = permits.removeValue(forKey: callback)
        let candidate = boundLease
        let allowed = !revoked
        lock.unlock()
        guard allowed, let permit, permit.request == request, permit.lease == candidate,
              ProcessInfo.processInfo.systemUptime - permit.issued >= 0,
              ProcessInfo.processInfo.systemUptime - permit.issued <= 30, isCurrent else { return nil }
        return permit.lease
    }

    /// Only the owned main reply path releases this window, after its WK drain callback.
    func complete(callback: String) {
        lock.lock(); defer { lock.unlock() }
        if activeCallback == callback { activeCallback = nil; permits.removeValue(forKey: callback) }
    }

    func adoptClear(_ acknowledgement: StorageAcknowledgement, previous: StorageLease) -> Bool {
        guard previous.generation < StorageLimits.maxCounter,
              acknowledgement.generation == previous.generation + 1 else { return false }
        let next = StorageLease(owner: previous.owner, authEpoch: previous.authEpoch,
                                launch: previous.launch, generation: acknowledgement.generation)
        guard hostIsActive(), coordinator.isCurrent(next) else { return false }
        lock.lock(); defer { lock.unlock() }
        guard !revoked, boundLease == previous else { return false }
        boundLease = next
        return true
    }
}

@objc(PrototypeStorePlugin)
final class PrototypeStorePlugin: CAPInstancePlugin, CAPBridgedPlugin {
    let identifier = "PrototypeStorePlugin"
    let jsName = "GSIPStoragePrototype"
    let pluginMethods: [CAPPluginMethod] = ["status", "put", "read", "remove", "clear"].map {
        CAPPluginMethod(name: $0, returnType: CAPPluginReturnPromise)
    }
    private var session: PrototypeStorageSession?
    private var delivery: ((CAPPluginCall, [String: Any]?, StorageLease, String) -> Void)?
    private static let recordKey = "synthetic-canary"

    func bind(_ session: PrototypeStorageSession, delivery: ((CAPPluginCall, [String: Any]?, StorageLease, String) -> Void)? = nil) -> Bool {
        guard self.session == nil, session.isCurrent else { return false }
        self.session = session
        self.delivery = delivery
        return true
    }

    static func bytes(for canary: String) -> Data? {
        switch canary {
        case "alpha": return Data("GSIP synthetic alpha".utf8)
        case "beta": return Data("GSIP synthetic beta".utf8)
        default: return nil
        }
    }

    /// The same parser protects direct native test calls and raw bridge dispatch.
    func process(method: String, options: [String: Any], expectedLease: StorageLease? = nil) -> [String: Any]? {
        guard let request = PrototypeWireRequest.parse(method: method, options: options),
              let session, session.isCurrent else { return nil }
        let lease = expectedLease ?? session.lease
        guard session.lease == lease else { return nil }
        switch request.method {
        case "status":
            guard session.isCurrent else { return nil }
            return ["state": "admitted", "logicalStores": LogicalStore.allCases.count]
        case "read":
            guard let store = request.store else { return nil }
            let outcome = session.coordinator.read(store: store, key: Self.recordKey, lease: lease)
            guard session.isCurrent, session.lease == lease else { return nil }
            switch outcome {
            case .absent: return ["state": "absent"]
            case let .found(record):
                let name: String
                if record.bytes == Self.bytes(for: "alpha") { name = "alpha" }
                else if record.bytes == Self.bytes(for: "beta") { name = "beta" }
                else { return nil }
                return ["state": "found", "canary": name, "recordRevision": record.revision]
            case .held: return nil
            }
        default:
            guard let operationID = request.operationID else { return nil }
            let mutation: StorageMutation
            switch request.method {
            case "put":
                guard let store = request.store, let canary = request.canary,
                      let bytes = Self.bytes(for: canary), let revision = request.expectedRevision else { return nil }
                mutation = .put(store: store, key: Self.recordKey, bytes: bytes, expectedRevision: revision)
            case "remove":
                guard let store = request.store, let revision = request.expectedRevision else { return nil }
                mutation = .remove(store: store, key: Self.recordKey, expectedRevision: revision)
            case "clear": mutation = .clear
            default: return nil
            }
            let outcome = session.coordinator.execute(StorageRequest(operationID: operationID, lease: lease, mutation: mutation))
            guard case let .acknowledged(acknowledgement) = outcome else { return nil }
            if request.method == "clear" {
                guard session.adoptClear(acknowledgement, previous: lease) else { return nil }
            } else {
                guard session.lease == lease else { return nil }
            }
            guard session.isCurrent else { return nil }
            return ["state": "acknowledged", "revision": acknowledgement.revision,
                    "generation": acknowledgement.generation, "recordRevision": acknowledgement.recordRevision,
                    "retry": acknowledgement.retry]
        }
    }

    private func reply(_ method: String, _ call: CAPPluginCall) {
        guard let options = call.options as? [String: Any], let session,
              let request = PrototypeWireRequest.parse(method: method, options: options),
              let lease = session.consume(callback: call.callbackId, request: request) else { return }
        let result = process(method: method, options: options, expectedLease: lease)
        guard let delivery else { session.complete(callback: call.callbackId); return }
        delivery(call, result, session.lease, call.callbackId)
    }

    @objc func status(_ call: CAPPluginCall) { reply("status", call) }
    @objc func put(_ call: CAPPluginCall) { reply("put", call) }
    @objc func read(_ call: CAPPluginCall) { reply("read", call) }
    @objc func remove(_ call: CAPPluginCall) { reply("remove", call) }
    @objc func clear(_ call: CAPPluginCall) { reply("clear", call) }
}
