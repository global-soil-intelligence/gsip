// SPDX-License-Identifier: MIT
import XCTest
import Foundation
import Darwin
import SQLite3
@testable import GSIPStorageCore

final class ExcludedSQLiteStoreTests: XCTestCase {
    private func fixture() throws -> (ExcludedSQLiteStore, SyntheticRunIdentity, SyntheticFixtureAuthority) {
        let authority = try requiredSimulatorAuthority()
        let identity = try KeychainAnchor.makeRunIdentity(authority: authority)
        return (try ExcludedSQLiteStore.createSyntheticFixture(authority: authority, identity: identity, owner: "synthetic-owner", protectedDataAvailable: { true }), identity, authority)
    }
    private func root(_ identity: SyntheticRunIdentity) -> URL {
        FileManager.default.urls(for: .libraryDirectory, in: .userDomainMask).first!.resolvingSymlinksInPath()
            .appendingPathComponent("GSIPStoragePrototype-v1").appendingPathComponent(identity.nonce)
    }
    private func scalar(_ sql: String, identity: SyntheticRunIdentity) throws -> Int64 {
        var pointer: OpaquePointer?
        let url = root(identity).appendingPathComponent("gsip-app2c2a.sqlite3")
        guard sqlite3_open_v2(url.path, &pointer, SQLITE_OPEN_READONLY, nil) == SQLITE_OK, let pointer else { throw StorageHold.unavailable }
        defer { sqlite3_close(pointer) }
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(pointer, sql, -1, &statement, nil) == SQLITE_OK, let statement else { throw StorageHold.unavailable }
        defer { sqlite3_finalize(statement) }
        guard sqlite3_step(statement) == SQLITE_ROW else { throw StorageHold.corrupt }
        return sqlite3_column_int64(statement, 0)
    }
    private func coordinated(_ store: ExcludedSQLiteStore) throws -> (StorageCoordinator, StorageLease, MemoryAnchor) {
        let trace = Trace(); let anchor = MemoryAnchor(.clean(try store.snapshot()), trace: trace)
        let coordinator = StorageCoordinator(database: store, anchor: anchor)
        let lease = syntheticLease(); XCTAssertTrue(coordinator.admit(lease: lease) == .admitted(lease))
        return (coordinator, lease, anchor)
    }
    func testUnavailableProtectedDataHoldsBeforeRootCreationOrSQLiteOpen() throws {
        let authority = try requiredSimulatorAuthority()
        let identity = try KeychainAnchor.makeRunIdentity(authority: authority)
        XCTAssertThrowsError(try ExcludedSQLiteStore.createSyntheticFixture(authority: authority, identity: identity,
                                                                           owner: "synthetic-owner", protectedDataAvailable: { false })) {
            XCTAssertTrue($0 as? StorageHold == .unavailable)
        }
        XCTAssertFalse(FileManager.default.fileExists(atPath: root(identity).path))
        let (store, existingIdentity, _) = try fixture(); try store.validateBoundary()
        XCTAssertThrowsError(try ExcludedSQLiteStore(authority: authority, identity: existingIdentity, protectedDataAvailable: { false })) {
            XCTAssertTrue($0 as? StorageHold == .unavailable)
        }
    }
    func testAvailabilityLossAfterAdmissionRevokesBeforeMutation() throws {
        let authority = try requiredSimulatorAuthority(); let identity = try KeychainAnchor.makeRunIdentity(authority: authority)
        var available = true
        let store = try ExcludedSQLiteStore.createSyntheticFixture(authority: authority, identity: identity,
                                                                   owner: "synthetic-owner", protectedDataAvailable: { available })
        let (coordinator, lease, _) = try coordinated(store)
        available = false
        XCTAssertTrue(coordinator.execute(syntheticPut()) == .held(.unavailable))
        XCTAssertFalse(coordinator.isCurrent(lease))
        available = true; XCTAssertEqual(try store.snapshot().revision, 0)
    }
    func testOnlyOneConcreteConnectionAndCoordinatorOwnTheSyntheticStore() throws {
        let (store, identity, authority) = try fixture()
        XCTAssertThrowsError(try ExcludedSQLiteStore(authority: authority, identity: identity, protectedDataAvailable: { true })) {
            XCTAssertTrue($0 as? StorageHold == .busy)
        }
        let (first, lease, anchor) = try coordinated(store)
        let second = StorageCoordinator(database: store, anchor: anchor)
        XCTAssertTrue(second.admit(lease: lease) == .held(.busy))
        XCTAssertTrue(first.isCurrent(lease)); XCTAssertFalse(second.isCurrent(lease))
    }
    func testActualSQLiteStoresExactBinaryAndSixStoreClearFences() throws {
        let (store, identity, _) = try fixture(); let (coordinator, lease, _) = try coordinated(store)
        for logical in LogicalStore.allCases where logical.isPayload {
            let request = StorageRequest(operationID: "put-" + logical.rawValue, lease: lease,
                                         mutation: .put(store: logical, key: "synthetic-canary", bytes: Data([0, 255, 1, 0]), expectedRevision: 0))
            guard case .acknowledged = coordinator.execute(request) else { return XCTFail("expected fixed mutation acknowledgement") }
            guard case let .found(record) = coordinator.read(store: logical, key: "synthetic-canary", lease: lease) else { return XCTFail("expected fixed record") }
            XCTAssertTrue(record.bytes == Data([0, 255, 1, 0])); XCTAssertTrue(record.revision > 0)
        }
        let clear = StorageRequest(operationID: "clear-all", lease: lease, mutation: .clear)
        guard case let .acknowledged(acknowledgement) = coordinator.execute(clear) else { return XCTFail("expected clear") }
        XCTAssertEqual(acknowledgement.generation, 1)
        XCTAssertEqual(try scalar("SELECT COUNT(*) FROM records", identity: identity), 0)
        XCTAssertEqual(try scalar("SELECT COUNT(*) FROM staging", identity: identity), 0)
        XCTAssertEqual(try scalar("SELECT generation FROM reminder WHERE id=1", identity: identity), 1)
        XCTAssertEqual(try scalar("SELECT enabled FROM reminder WHERE id=1", identity: identity), 0)
        XCTAssertEqual(try scalar("SELECT cleanup_pending FROM reminder WHERE id=1", identity: identity), 1)
        XCTAssertFalse(coordinator.isCurrent(lease)); try store.validateBoundary()
    }
    func testActualSQLiteReadbacksAndExcludedPolicyPrecedeReopen() throws {
        let (store, identity, authority) = try fixture()
        try store.validateBoundary()
        XCTAssertEqual(try scalar("PRAGMA user_version", identity: identity), 1)
        let actual = try store.runtimeEvidence()
        XCTAssertTrue(actual.journalMode == "delete")
        XCTAssertEqual(actual.synchronous, 3); XCTAssertEqual(actual.foreignKeys, 1)
        XCTAssertEqual(actual.tempStore, 2); XCTAssertEqual(actual.busyMilliseconds, 250)
        XCTAssertEqual(actual.attachedLimit, 0)
        XCTAssertFalse(actual.version.isEmpty); XCTAssertFalse(actual.sourceID.isEmpty)
        let databaseURL = root(identity).appendingPathComponent("gsip-app2c2a.sqlite3")
        let policy = try databaseURL.resourceValues(forKeys: [.isExcludedFromBackupKey])
        XCTAssertTrue(policy.isExcludedFromBackup == true)
        var mutableRoot = root(identity); var values = URLResourceValues(); values.isExcludedFromBackup = false
        try mutableRoot.setResourceValues(values)
        XCTAssertThrowsError(try store.validateBoundary())
        XCTAssertThrowsError(try ExcludedSQLiteStore(authority: authority, identity: identity, protectedDataAvailable: { true }))
    }
    func testDatabaseLeafSymlinkHardlinkAndReplacementAreRefused() throws {
        for mode in 0..<3 {
            let (store, identity, authority) = try fixture()
            let database = root(identity).appendingPathComponent("gsip-app2c2a.sqlite3")
            let moved = root(identity).appendingPathComponent("owned-original")
            if mode == 0 {
                try FileManager.default.moveItem(at: database, to: moved)
                try FileManager.default.createSymbolicLink(at: database, withDestinationURL: moved)
            } else if mode == 1 {
                try FileManager.default.linkItem(at: database, to: moved)
            } else {
                try FileManager.default.moveItem(at: database, to: moved)
                let descriptor = Darwin.open(database.path, O_RDWR | O_CREAT | O_EXCL | O_NOFOLLOW, 0o600)
                XCTAssertTrue(descriptor >= 0)
                if descriptor >= 0 { Darwin.close(descriptor) }
            }
            XCTAssertThrowsError(try store.validateBoundary())
            XCTAssertThrowsError(try ExcludedSQLiteStore(authority: authority, identity: identity, protectedDataAvailable: { true }))
        }
    }
    func testRootSymlinkReplacementAndUnknownSidecarsAreRefused() throws {
        let (store, identity, _) = try fixture()
        let unknown = root(identity).appendingPathComponent("unknown-sidecar")
        let descriptor = Darwin.open(unknown.path, O_RDWR | O_CREAT | O_EXCL | O_NOFOLLOW, 0o600)
        XCTAssertTrue(descriptor >= 0); if descriptor >= 0 { Darwin.close(descriptor) }
        XCTAssertThrowsError(try store.validateBoundary())
        let (second, otherIdentity, _) = try fixture()
        let original = root(otherIdentity)
        let moved = original.deletingLastPathComponent().appendingPathComponent(otherIdentity.nonce + "-owned-old")
        try FileManager.default.moveItem(at: original, to: moved)
        try FileManager.default.createSymbolicLink(at: original, withDestinationURL: moved)
        XCTAssertThrowsError(try second.validateBoundary())
    }
    func testIncompleteStagingIsNotSavedAndWrongHashCannotFinish() throws {
        let (store, identity, _) = try fixture(); let (coordinator, lease, _) = try coordinated(store)
        let begin = StorageRequest(operationID: "stage-one", lease: lease,
                                   mutation: .beginStage(store: .draftPhotos, key: "synthetic-canary", length: 3,
                                                         sha256: String(repeating: "a", count: 64), expectedRevision: 0))
        guard case .staged = coordinator.execute(begin) else { return XCTFail("expected staging only") }
        XCTAssertTrue(coordinator.read(store: .draftPhotos, key: "synthetic-canary", lease: lease) == .absent)
        let append = StorageRequest(operationID: "stage-chunk", lease: lease,
                                    mutation: .appendStage(stageID: "stage-one", offset: 0, bytes: Data([1, 2, 3])))
        guard case .staged = coordinator.execute(append) else { return XCTFail("expected staging only") }
        let finish = StorageRequest(operationID: "stage-finish", lease: lease, mutation: .finishStage(stageID: "stage-one"))
        XCTAssertTrue(coordinator.execute(finish) == .held(.invalidRequest))
        XCTAssertEqual(try scalar("SELECT COUNT(*) FROM staging", identity: identity), 1)
        let clear = StorageRequest(operationID: "clear-stage", lease: lease, mutation: .clear)
        guard case .acknowledged = coordinator.execute(clear) else { return XCTFail("expected clear") }
        XCTAssertEqual(try scalar("SELECT COUNT(*) FROM staging", identity: identity), 0)
    }
    func testStageHashAndBinaryLengthMustMatchBeforeAtomicPublication() throws {
        let (store, _, _) = try fixture(); let (coordinator, lease, _) = try coordinated(store)
        // SHA256 of ASCII abc, a published synthetic known-answer vector.
        let digest = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        let begin = StorageRequest(operationID: "good-stage", lease: lease,
                                   mutation: .beginStage(store: .libraryDraft, key: "synthetic-canary", length: 3, sha256: digest, expectedRevision: 0))
        guard case .staged = coordinator.execute(begin) else { return XCTFail("expected staging") }
        let premature = StorageRequest(operationID: "too-soon", lease: lease, mutation: .finishStage(stageID: "good-stage"))
        XCTAssertTrue(coordinator.execute(premature) == .held(.invalidRequest))
        let append = StorageRequest(operationID: "good-chunk", lease: lease, mutation: .appendStage(stageID: "good-stage", offset: 0, bytes: Data([97, 98, 99])))
        guard case .staged = coordinator.execute(append) else { return XCTFail("expected chunk staging") }
        let finish = StorageRequest(operationID: "good-finish", lease: lease, mutation: .finishStage(stageID: "good-stage"))
        guard case .acknowledged = coordinator.execute(finish) else { return XCTFail("expected complete save") }
        guard case let .found(record) = coordinator.read(store: .libraryDraft, key: "synthetic-canary", lease: lease) else { return XCTFail("expected complete record") }
        XCTAssertTrue(record.bytes == Data([97, 98, 99]))
    }
    func testRemoveRecreateNeverReusesRecordRevision() throws {
        let (store, _, _) = try fixture(); let (coordinator, lease, _) = try coordinated(store)
        guard case let .acknowledged(first) = coordinator.execute(syntheticPut()) else { return XCTFail("expected initial mutation") }
        let remove = StorageRequest(operationID: "remove-one", lease: lease,
                                    mutation: .remove(store: .submissions, key: "synthetic-canary", expectedRevision: first.recordRevision))
        guard case .acknowledged = coordinator.execute(remove) else { return XCTFail("expected remove") }
        guard case let .acknowledged(recreated) = coordinator.execute(syntheticPut("recreate")) else { return XCTFail("expected recreate") }
        XCTAssertGreaterThan(recreated.recordRevision, first.recordRevision)
        let stale = syntheticPut("old-record-callback", revision: first.recordRevision)
        XCTAssertTrue(coordinator.execute(stale) == .held(.revisionMismatch))
    }
    func testReceiptUniquenessFailureRollsBackEverySQLiteMutation() throws {
        let (store, identity, _) = try fixture(); let (coordinator, lease, anchor) = try coordinated(store)
        store.injectReceiptConstraintFaultForSyntheticTest()
        XCTAssertTrue(coordinator.execute(syntheticPut()) == .held(.unavailable))
        XCTAssertFalse(coordinator.isCurrent(lease)); XCTAssertEqual(anchor.value?.phase, .pending)
        XCTAssertEqual(try store.snapshot().revision, 0)
        XCTAssertEqual(try scalar("SELECT COUNT(*) FROM records", identity: identity), 0)
        XCTAssertEqual(try scalar("SELECT COUNT(*) FROM receipts", identity: identity), 0)
        XCTAssertEqual(try scalar("SELECT revision FROM reminder WHERE id=1", identity: identity), 0)
    }
    func testSameVersionUnexpectedTableOrTriggerIsHeld() throws {
        for trigger in [false, true] {
            let (store, identity, _) = try fixture(); let (coordinator, lease, anchor) = try coordinated(store)
            var pointer: OpaquePointer?
            let url = root(identity).appendingPathComponent("gsip-app2c2a.sqlite3")
            guard sqlite3_open_v2(url.path, &pointer, SQLITE_OPEN_READWRITE, nil) == SQLITE_OK, let pointer else { throw StorageHold.unavailable }
            let sql = trigger ? "CREATE TRIGGER synthetic_extra AFTER INSERT ON records BEGIN SELECT 1; END" : "CREATE TABLE synthetic_extra(value INTEGER)"
            let code = sqlite3_exec(pointer, sql, nil, nil, nil); sqlite3_close(pointer)
            XCTAssertEqual(code, SQLITE_OK)
            XCTAssertTrue(coordinator.execute(syntheticPut()) == .held(.unknownSchema))
            XCTAssertFalse(coordinator.isCurrent(lease)); XCTAssertEqual(anchor.value?.phase, .clean)
            XCTAssertEqual(try scalar("SELECT COUNT(*) FROM records", identity: identity), 0)
            XCTAssertEqual(try scalar("SELECT COUNT(*) FROM receipts", identity: identity), 0)
        }
    }
    func testActualSQLiteBusyTimeoutHoldsWithoutReceipt() throws {
        let (store, identity, _) = try fixture(); let (coordinator, _, anchor) = try coordinated(store)
        var competing: OpaquePointer?
        let url = root(identity).appendingPathComponent("gsip-app2c2a.sqlite3")
        guard sqlite3_open_v2(url.path, &competing, SQLITE_OPEN_READWRITE, nil) == SQLITE_OK, let competing else { throw StorageHold.unavailable }
        defer { sqlite3_exec(competing, "ROLLBACK", nil, nil, nil); sqlite3_close(competing) }
        XCTAssertEqual(sqlite3_exec(competing, "BEGIN EXCLUSIVE", nil, nil, nil), SQLITE_OK)
        XCTAssertTrue(coordinator.execute(syntheticPut()) == .held(.busy))
        XCTAssertEqual(anchor.value?.phase, .clean)
        XCTAssertEqual(sqlite3_exec(competing, "ROLLBACK", nil, nil, nil), SQLITE_OK)
        XCTAssertEqual(try scalar("SELECT COUNT(*) FROM receipts", identity: identity), 0)
    }
    func testCorruptedOwnedDatabaseIsRefusedWithoutNewSchema() throws {
        let authority = try requiredSimulatorAuthority(); let identity = try KeychainAnchor.makeRunIdentity(authority: authority)
        var owned: ExcludedSQLiteStore? = try ExcludedSQLiteStore.createSyntheticFixture(authority: authority, identity: identity,
                                                                                        owner: "synthetic-owner", protectedDataAvailable: { true })
        weak var released = owned; owned = nil; XCTAssertTrue(released == nil)
        let url = root(identity).appendingPathComponent("gsip-app2c2a.sqlite3")
        let descriptor = Darwin.open(url.path, O_RDWR | O_NOFOLLOW)
        guard descriptor >= 0 else { throw StorageHold.boundary }
        let bytes = [UInt8](repeating: 0x7f, count: 32)
        let written = bytes.withUnsafeBytes { Darwin.write(descriptor, $0.baseAddress, $0.count) }
        Darwin.close(descriptor); XCTAssertEqual(written, 32)
        XCTAssertThrowsError(try ExcludedSQLiteStore(authority: authority, identity: identity, protectedDataAvailable: { true })) {
            XCTAssertTrue($0 as? StorageHold == .corrupt)
        }
    }
    func testInvalidGenerationQuotaAndRevisionDoNotCreateReceipts() throws {
        let (store, identity, _) = try fixture(); let (coordinator, lease, _) = try coordinated(store)
        XCTAssertTrue(coordinator.execute(syntheticPut(revision: 1)) == .held(.revisionMismatch))
        let tooLarge = StorageRequest(operationID: "over-capacity", lease: lease,
                                      mutation: .beginStage(store: .submissions, key: "synthetic-canary", length: StorageLimits.managedBytes,
                                                            sha256: String(repeating: "b", count: 64), expectedRevision: 0))
        XCTAssertTrue(coordinator.execute(tooLarge) == .held(.quota))
        XCTAssertEqual(try scalar("SELECT COUNT(*) FROM receipts", identity: identity), 0)
    }
}
