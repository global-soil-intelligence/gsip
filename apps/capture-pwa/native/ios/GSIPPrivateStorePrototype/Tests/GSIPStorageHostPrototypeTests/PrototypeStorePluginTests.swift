// SPDX-License-Identifier: MIT
import XCTest
import Foundation
import Capacitor
import GSIPStorageCore
@testable import App

/// Injected protocol doubles only; these cannot certify SQLite or Keychain behavior.
final class HostSyntheticDatabase: StorageDatabase {
    var value = DatabaseSnapshot(installation: "synthetic-install", owner: "synthetic-owner", authEpoch: 0,
                                 revision: 0, generation: 0, commitNonce: "synthetic-initial")
    var records: [String: StorageRecord] = [:]
    var receipts: [String: OperationReceipt] = [:]
    var boundaryValid = true
    var afterCommitValidation: (() -> Void)?
    var committed = false
    func validateBoundary() throws {
        guard boundaryValid else { throw StorageHold.boundary }
        if committed { afterCommitValidation?() }
    }
    func snapshot() throws -> DatabaseSnapshot { value }
    func digest(_ request: StorageRequest) throws -> String {
        // Deliberately non-cryptographic test double; production SHA256 lives in the core store.
        let bytes = try JSONEncoder().encode(request)
        let total = bytes.reduce(UInt64(0)) { $0 + UInt64($1) }
        return String(format: "%064llx", total)
    }
    func receipt(operationID: String) throws -> OperationReceipt? { receipts[operationID] }
    func prepare(_ request: StorageRequest) throws {
        switch request.mutation {
        case let .put(store, key, _, expectedRevision), let .remove(store, key, expectedRevision):
            guard (records[store.rawValue + ":" + key]?.revision ?? 0) == expectedRevision else { throw StorageHold.revisionMismatch }
        case .clear: break
        default: throw StorageHold.invalidRequest
        }
    }
    func commit(_ request: StorageRequest, next: DatabaseSnapshot, digest: String) throws -> OperationReceipt {
        var recordRevision: UInt64 = 0
        switch request.mutation {
        case let .put(store, key, bytes, expectedRevision):
            recordRevision = expectedRevision + 1
            records[store.rawValue + ":" + key] = StorageRecord(bytes: bytes, revision: recordRevision)
        case let .remove(store, key, expectedRevision):
            recordRevision = expectedRevision + 1
            records.removeValue(forKey: store.rawValue + ":" + key)
        case .clear: records.removeAll()
        default: throw StorageHold.invalidRequest
        }
        value = next
        committed = true
        let acknowledgement = StorageAcknowledgement(operationID: request.operationID, revision: next.revision,
                                                      generation: next.generation, recordRevision: recordRevision)
        let receipt = OperationReceipt(requestDigest: digest, lease: request.lease,
                                       commitNonce: next.commitNonce, acknowledgement: acknowledgement,
                                       kind: request.mutation.kind)
        receipts[request.operationID] = receipt
        return receipt
    }
    func read(store: LogicalStore, key: String) throws -> StorageRecord? { records[store.rawValue + ":" + key] }
}

final class HostSyntheticAnchor: StorageAnchor {
    var state: AnchorState?
    var calls = 0
    init(snapshot: DatabaseSnapshot) { state = .clean(snapshot) }
    func read() throws -> AnchorState? { state }
    func update(_ state: AnchorState, expecting: AnchorState) throws {
        guard self.state == expecting else { throw StorageHold.anchorMismatch }
        self.state = state
    }
    func freshNonce() throws -> String { calls += 1; return "synthetic-nonce-" + String(calls) }
}

final class HostSyntheticFixture {
    let database = HostSyntheticDatabase()
    let anchor: HostSyntheticAnchor
    let coordinator: StorageCoordinator
    let lease = StorageLease(owner: "synthetic-owner", authEpoch: 0, launch: "synthetic-launch", generation: 0)
    var active = true
    init() {
        anchor = HostSyntheticAnchor(snapshot: database.value)
        coordinator = StorageCoordinator(database: database, anchor: anchor)
    }
    func admit() -> StorageAdmission { coordinator.admit(lease: lease) }
    func session() -> PrototypeStorageSession {
        PrototypeStorageSession(coordinator: coordinator, lease: lease, hostIsActive: { [weak self] in self?.active == true })
    }
}

final class PrototypeStorePluginTests: XCTestCase {
    func testOnlyFixedCanariesAndPayloadStoresAreAccepted() {
        let fixture = HostSyntheticFixture()
        XCTAssertTrue(fixture.admit() == .admitted(fixture.lease))
        let session = fixture.session()
        let plugin = PrototypeStorePlugin()
        XCTAssertTrue(plugin.bind(session))
        XCTAssertFalse(plugin.bind(session))
        let options: [String: Any] = ["store": "submissions", "operationID": "synthetic-put", "expectedRevision": 0, "canary": "alpha"]
        XCTAssertTrue((plugin.process(method: "put", options: options)?["state"] as? String) == ("acknowledged"))
        XCTAssertTrue((plugin.process(method: "read", options: ["store": "submissions"])?["canary"] as? String) == ("alpha"))
        XCTAssertTrue((plugin.process(method: "put", options: options.merging(["path": "/synthetic"]){ _, new in new })) == nil)
        XCTAssertTrue((plugin.process(method: "executeSQL", options: [:])) == nil)
        XCTAssertTrue((plugin.process(method: "read", options: ["store": "syncReminder"])) == nil)
        XCTAssertTrue((plugin.process(method: "read", options: ["store": "queueState"])) == nil)
        XCTAssertTrue((plugin.process(method: "put", options: ["store": "submissions", "operationID": "synthetic-bad", "expectedRevision": 1, "canary": "unknown"])) == nil)
    }

    func testClearAdoptsOnlyAcknowledgedNativeGenerationAndRevokesOldLease() {
        let fixture = HostSyntheticFixture()
        XCTAssertTrue(fixture.admit() == .admitted(fixture.lease))
        let session = fixture.session()
        let plugin = PrototypeStorePlugin()
        XCTAssertTrue(plugin.bind(session))
        let reply = plugin.process(method: "clear", options: ["operationID": "synthetic-clear"])
        XCTAssertTrue((reply?["state"] as? String) == ("acknowledged"))
        XCTAssertTrue((reply?["generation"] as? UInt64) == (1))
        XCTAssertFalse(fixture.coordinator.isCurrent(fixture.lease))
        XCTAssertTrue(session.isCurrent)
        XCTAssertTrue((session.lease.generation) == (1))
        XCTAssertTrue((plugin.process(method: "clear", options: ["operationID": "synthetic-clear", "generation": 0])) == nil)
    }

    func testHostRevocationBetweenCommitAndReplySuppressesSuccess() {
        let fixture = HostSyntheticFixture()
        XCTAssertTrue(fixture.admit() == .admitted(fixture.lease))
        let session = fixture.session()
        let plugin = PrototypeStorePlugin()
        XCTAssertTrue(plugin.bind(session))
        fixture.database.afterCommitValidation = { fixture.active = false }
        XCTAssertTrue((plugin.process(method: "put", options: ["store": "draftPhotos", "operationID": "synthetic-race", "expectedRevision": 0, "canary": "beta"])) == nil)
        XCTAssertTrue((fixture.database.value.revision) == (1))
        XCTAssertFalse(session.isCurrent)
    }

    func testNativePluginCallbackRejectsHeldWithoutPrivateDetails() {
        let plugin = PrototypeStorePlugin()
        var success = false
        var replied = false
        let call = CAPPluginCall(callbackId: "synthetic-callback", methodName: "status", options: [:], success: { _, _ in
            success = true
        }, error: { _ in replied = true })
        plugin.status(call!)
        XCTAssertFalse(success)
        XCTAssertFalse(replied)
    }

    func testQueuedPermitCannotCrossClearGenerationOrBeReused() throws {
        let fixture = HostSyntheticFixture()
        XCTAssertTrue(fixture.admit() == .admitted(fixture.lease))
        let session = fixture.session()
        let plugin = PrototypeStorePlugin()
        XCTAssertTrue(plugin.bind(session))
        let oldRequest = try XCTUnwrap(PrototypeWireRequest.parse(method: "put", options: ["store": "submissions", "operationID": "synthetic-queued", "expectedRevision": 0, "canary": "alpha"]))
        XCTAssertTrue(session.register(callback: "synthetic-old", request: oldRequest))
        XCTAssertFalse(session.register(callback: "synthetic-old", request: oldRequest))
        XCTAssertTrue((plugin.process(method: "clear", options: ["operationID": "synthetic-generation"])) != nil)
        XCTAssertTrue((session.consume(callback: "synthetic-old", request: oldRequest)) == nil)
        XCTAssertFalse(session.register(callback: "synthetic-old", request: oldRequest))
        XCTAssertTrue(fixture.database.records.isEmpty)
        session.revoke()
        XCTAssertFalse(session.isCurrent)
        XCTAssertFalse(session.register(callback: "synthetic-new", request: oldRequest))
    }

    func testRawNativeCallbackNeedsMatchingSingleUsePermit() throws {
        let fixture = HostSyntheticFixture()
        XCTAssertTrue(fixture.admit() == .admitted(fixture.lease))
        let session = fixture.session()
        let plugin = PrototypeStorePlugin()
        XCTAssertTrue(plugin.bind(session, delivery: { call, result, lease, callback in
            // Injected synchronous delivery only, not an asynchronous WK boundary proof.
            guard session.isCurrent, session.lease == lease else { return }
            if let result { call.resolve(result) }
            else { call.reject("Synthetic storage is held.", "held") }
            session.complete(callback: callback)
        }))
        let status = try XCTUnwrap(PrototypeWireRequest.parse(method: "status", options: [:]))
        XCTAssertTrue(session.register(callback: "synthetic-once", request: status))
        var successes = 0
        var rejections = 0
        let call = CAPPluginCall(callbackId: "synthetic-once", methodName: "status", options: [:], success: { _, _ in
            successes += 1
        }, error: { _ in rejections += 1 })
        plugin.status(call!)
        plugin.status(call!)
        XCTAssertTrue(successes == 1 && rejections == 0)
    }

    func testAuthorityFieldsAndUnsafeCountersCannotEnterNativeRequest() {
        for field in ["owner", "authEpoch", "launch", "generation", "path", "sql", "key", "bytes", "nonce", "session"] {
            XCTAssertTrue((PrototypeWireRequest.parse(method: "status", options: [field: "synthetic"])) == nil)
        }
        for value in [true, -1, 0.5, Double.infinity, Double(StorageLimits.maxCounter) + 1] as [Any] {
            XCTAssertTrue((PrototypeWireRequest.parse(method: "put", options: ["store": "submissions", "operationID": "synthetic-op", "expectedRevision": value, "canary": "alpha"])) == nil)
        }
    }
}
