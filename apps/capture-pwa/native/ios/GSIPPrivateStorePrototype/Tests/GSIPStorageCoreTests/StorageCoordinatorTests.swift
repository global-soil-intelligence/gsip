// SPDX-License-Identifier: MIT
import XCTest
import Foundation
import Dispatch
@testable import GSIPStorageCore

final class StorageCoordinatorTests: XCTestCase {
    private func fixture(revision: UInt64 = 0, generation: UInt64 = 0) -> (StorageCoordinator, MemoryDatabase, MemoryAnchor, Trace) {
        let trace = Trace(); let snapshot = syntheticSnapshot(revision: revision, generation: generation)
        let database = MemoryDatabase(state: snapshot, trace: trace)
        let anchor = MemoryAnchor(.clean(snapshot), trace: trace)
        return (StorageCoordinator(database: database, anchor: anchor), database, anchor, trace)
    }
    func testCoordinatorRunsAnchorCallsOffMainThread() {
        let (coordinator, _, anchor, _) = fixture()
        XCTAssertTrue(coordinator.admit(lease: syntheticLease()) == .admitted(syntheticLease()))
        guard case .acknowledged = coordinator.execute(syntheticPut()) else { return XCTFail("expected mutation") }
        XCTAssertFalse(anchor.observedMainThread)
    }
    func testTimeoutAfterPendingWritePermanentlyFencesLateWork() {
        let trace = Trace(), snapshot = syntheticSnapshot()
        let database = MemoryDatabase(state: snapshot, trace: trace)
        let anchor = MemoryAnchor(.clean(snapshot), trace: trace)
        let coordinator = StorageCoordinator(database: database, anchor: anchor, timeoutMilliseconds: 100)
        XCTAssertTrue(coordinator.admit(lease: syntheticLease()) == .admitted(syntheticLease()))
        anchor.pendingDelay = 0.3
        XCTAssertTrue(coordinator.execute(syntheticPut()) == .held(.interrupted))
        XCTAssertFalse(coordinator.isCurrent(syntheticLease()))
        Thread.sleep(forTimeInterval: 0.5)
        XCTAssertEqual(database.commitCount, 0); XCTAssertEqual(anchor.value?.phase, .pending)
        XCTAssertTrue(coordinator.admit(lease: syntheticLease()) == .held(.interrupted))
        XCTAssertTrue(coordinator.execute(syntheticPut()) == .held(.interrupted))
    }
    func testTimedOutRecoveryCannotCleanPendingAnchorLater() {
        let (coordinator, database, anchor, _) = fixture()
        _ = coordinator.admit(lease: syntheticLease()); anchor.failClean = true
        XCTAssertTrue(coordinator.execute(syntheticPut()) == .held(.unavailable))
        anchor.failClean = false; database.receiptDelay = 0.3
        let recovering = StorageCoordinator(database: database, anchor: anchor, timeoutMilliseconds: 100)
        XCTAssertTrue(recovering.admit(lease: syntheticLease()) == .held(.interrupted))
        Thread.sleep(forTimeInterval: 0.5)
        XCTAssertEqual(anchor.value?.phase, .pending)
        XCTAssertFalse(recovering.isCurrent(syntheticLease()))
    }
    func testAcknowledgementFollowsPendingCommitCleanAndBoundary() {
        let (coordinator, database, _, trace) = fixture()
        XCTAssertTrue(coordinator.admit(lease: syntheticLease()) == .admitted(syntheticLease()))
        trace.events = []
        guard case .acknowledged = coordinator.execute(syntheticPut()) else { return XCTFail("expected bounded acknowledgement") }
        XCTAssertEqual(database.commitCount, 1)
        let pending = trace.events.firstIndex(of: "anchor-pending")!
        let commit = trace.events.firstIndex(of: "db-commit")!
        let clean = trace.events.firstIndex(of: "anchor-clean")!
        XCTAssertLessThan(pending, commit); XCTAssertLessThan(commit, clean)
        XCTAssertEqual(trace.events.last, "boundary")
    }
    func testLostReplyRetryDoesNotMutateTwiceAndChangedPayloadIsRefused() {
        let (coordinator, database, _, _) = fixture()
        _ = coordinator.admit(lease: syntheticLease())
        _ = coordinator.execute(syntheticPut())
        guard case let .acknowledged(acknowledgement) = coordinator.execute(syntheticPut()) else { return XCTFail("expected retry") }
        XCTAssertTrue(acknowledgement.retry); XCTAssertEqual(database.commitCount, 1)
        XCTAssertTrue(coordinator.execute(syntheticPut(bytes: Data([2]))) == .held(.operationConflict))
        XCTAssertEqual(database.commitCount, 1)
    }
    func testPendingBeforeFailedCommitPreservesAnchorAndQuarantinesRestart() {
        let (coordinator, database, anchor, _) = fixture()
        _ = coordinator.admit(lease: syntheticLease()); database.failCommit = true
        XCTAssertTrue(coordinator.execute(syntheticPut()) == .held(.interrupted))
        XCTAssertEqual(database.state.revision, 0); XCTAssertEqual(anchor.value?.phase, .pending)
        let restart = StorageCoordinator(database: database, anchor: anchor)
        XCTAssertTrue(restart.admit(lease: syntheticLease()) == .held(.pendingOldDatabase))
        XCTAssertEqual(database.commitCount, 0)
    }
    func testInjectedFullBusyAndIOFailuresNeverAcknowledgeOrRollbackAnchor() {
        for failure in [StorageHold.quota, .busy, .unavailable] {
            let (coordinator, database, anchor, _) = fixture()
            _ = coordinator.admit(lease: syntheticLease()); database.failCommit = true; database.commitError = failure
            XCTAssertTrue(coordinator.execute(syntheticPut()) == .held(failure))
            XCTAssertEqual(database.state.revision, 0); XCTAssertEqual(anchor.value?.phase, .pending)
            XCTAssertFalse(coordinator.isCurrent(syntheticLease()))
        }
    }
    func testPendingWithMatchingCommittedReceiptCanFinalize() {
        let (coordinator, database, anchor, _) = fixture()
        _ = coordinator.admit(lease: syntheticLease()); anchor.failClean = true
        XCTAssertTrue(coordinator.execute(syntheticPut()) == .held(.unavailable))
        XCTAssertEqual(database.commitCount, 1); XCTAssertEqual(anchor.value?.phase, .pending)
        anchor.failClean = false
        let restart = StorageCoordinator(database: database, anchor: anchor)
        XCTAssertTrue(restart.admit(lease: syntheticLease()) == .admitted(syntheticLease()))
        XCTAssertEqual(anchor.value?.phase, .clean)
        guard case .acknowledged = restart.execute(syntheticPut()) else { return XCTFail("expected matching receipt retry") }
        XCTAssertEqual(database.commitCount, 1)
    }
    func testPendingWriteWhoseReadbackFailsRevokesAdmission() {
        let (coordinator, database, anchor, _) = fixture()
        _ = coordinator.admit(lease: syntheticLease()); anchor.failPendingAfterWrite = true
        XCTAssertTrue(coordinator.execute(syntheticPut()) == .held(.unavailable))
        XCTAssertFalse(coordinator.isCurrent(syntheticLease()))
        XCTAssertEqual(anchor.value?.phase, .pending); XCTAssertEqual(database.commitCount, 0)
    }
    func testReadmissionUnknownStateRevokesEarlierAdmission() {
        let (coordinator, _, anchor, _) = fixture()
        _ = coordinator.admit(lease: syntheticLease()); anchor.value = nil
        XCTAssertTrue(coordinator.admit(lease: syntheticLease()) == .held(.missingAnchor))
        XCTAssertFalse(coordinator.isCurrent(syntheticLease()))
    }
    func testChangedDatabaseControlRevokesPreviouslyCurrentLease() {
        for useRead in [true, false] {
            let (coordinator, database, _, _) = fixture(); _ = coordinator.admit(lease: syntheticLease())
            database.state = syntheticSnapshot(generation: 1)
            if useRead { XCTAssertTrue(coordinator.read(store: .submissions, key: "synthetic-canary", lease: syntheticLease()) == .held(.staleLease)) }
            else { XCTAssertTrue(coordinator.execute(syntheticPut()) == .held(.staleLease)) }
            XCTAssertFalse(coordinator.isCurrent(syntheticLease()))
        }
    }
    func testUnknownPendingReceiptDoesNotCleanAnchor() {
        let (coordinator, database, anchor, _) = fixture()
        _ = coordinator.admit(lease: syntheticLease()); anchor.failClean = true
        _ = coordinator.execute(syntheticPut()); database.receipts.removeAll(); anchor.failClean = false
        let restart = StorageCoordinator(database: database, anchor: anchor)
        XCTAssertTrue(restart.admit(lease: syntheticLease()) == .held(.unknownReceipt))
        XCTAssertEqual(anchor.value?.phase, .pending)
    }
    func testMissingOrUnknownAnchorNeverInitializes() {
        let (coordinator, database, anchor, _) = fixture(); anchor.value = nil
        XCTAssertTrue(coordinator.admit(lease: syntheticLease()) == .held(.missingAnchor))
        XCTAssertTrue(anchor.value == nil); XCTAssertEqual(database.commitCount, 0)
        anchor.failRead = true
        XCTAssertTrue(coordinator.admit(lease: syntheticLease()) == .held(.unavailable))
    }
    func testBoundaryFailureBeforeAdmissionOrAfterCommitNeverAcknowledges() {
        let (coordinator, database, anchor, _) = fixture(); database.failBoundary = true
        XCTAssertTrue(coordinator.admit(lease: syntheticLease()) == .held(.boundary)); XCTAssertEqual(database.commitCount, 0)
        database.failBoundary = false; _ = coordinator.admit(lease: syntheticLease()); database.failPostBoundary = true
        XCTAssertTrue(coordinator.execute(syntheticPut()) == .held(.boundary))
        XCTAssertEqual(anchor.value?.phase, .clean); XCTAssertFalse(coordinator.isCurrent(syntheticLease()))
    }
    func testCounterExhaustionHoldsBeforeAnchorMutation() {
        let (coordinator, database, anchor, _) = fixture(revision: StorageLimits.maxCounter)
        _ = coordinator.admit(lease: syntheticLease())
        XCTAssertTrue(coordinator.execute(syntheticPut()) == .held(.exhausted))
        XCTAssertEqual(anchor.value?.phase, .clean); XCTAssertEqual(database.commitCount, 0)
    }
    func testStaleLeaseEpochOwnerGenerationAndRecordRevisionAreFenced() {
        let (coordinator, database, _, _) = fixture(); _ = coordinator.admit(lease: syntheticLease())
        let leases = [StorageLease(owner: "foreign", authEpoch: 0, launch: "synthetic-launch", generation: 0),
                      StorageLease(owner: "synthetic-owner", authEpoch: 1, launch: "synthetic-launch", generation: 0),
                      syntheticLease(launch: "obsolete"), syntheticLease(generation: 1)]
        for lease in leases { XCTAssertTrue(coordinator.execute(syntheticPut(lease: lease)) == .held(.staleLease)) }
        XCTAssertEqual(database.commitCount, 0)
        XCTAssertTrue(coordinator.execute(syntheticPut(revision: 1)) == .held(.revisionMismatch))
    }
    func testClearAdvancesGenerationAndRejectsOldLease() {
        let (coordinator, database, _, _) = fixture(); _ = coordinator.admit(lease: syntheticLease())
        _ = coordinator.execute(syntheticPut())
        let clear = StorageRequest(operationID: "clear-one", lease: syntheticLease(), mutation: .clear)
        guard case .acknowledged = coordinator.execute(clear) else { return XCTFail("expected clear") }
        XCTAssertTrue(database.records.isEmpty); XCTAssertEqual(database.state.generation, 1)
        XCTAssertFalse(coordinator.isCurrent(syntheticLease()))
        XCTAssertTrue(coordinator.isCurrent(syntheticLease(generation: 1)))
        guard case let .acknowledged(retry) = coordinator.execute(clear) else { return XCTFail("expected exact clear receipt retry") }
        XCTAssertTrue(retry.retry); XCTAssertEqual(database.state.generation, 1)
        let foreignClear = StorageRequest(operationID: "different-clear", lease: syntheticLease(), mutation: .clear)
        XCTAssertTrue(coordinator.execute(foreignClear) == .held(.staleLease))
        XCTAssertTrue(coordinator.execute(syntheticPut("after-clear")) == .held(.staleLease))
    }
    func testSuspensionAndConcurrentDuplicateSerialize() {
        let (coordinator, database, _, _) = fixture(); _ = coordinator.admit(lease: syntheticLease())
        DispatchQueue.concurrentPerform(iterations: 8) { _ in _ = coordinator.execute(syntheticPut()) }
        XCTAssertEqual(database.commitCount, 1)
        coordinator.suspend(); XCTAssertFalse(coordinator.isCurrent(syntheticLease()))
        XCTAssertTrue(coordinator.execute(syntheticPut()) == .held(.suspended))
    }
    func testRequestAndReadBoundsRejectMalformedValues() {
        let (coordinator, _, _, _) = fixture(); _ = coordinator.admit(lease: syntheticLease())
        XCTAssertTrue(coordinator.execute(syntheticPut(bytes: Data(repeating: 0, count: StorageLimits.chunkBytes + 1))) == .held(.invalidRequest))
        XCTAssertTrue(coordinator.read(store: .submissions, key: "../other", lease: syntheticLease()) == .held(.invalidRequest))
        XCTAssertTrue(coordinator.admit(lease: StorageLease(owner: "synthetic-owner", authEpoch: StorageLimits.maxCounter + 1, launch: "new", generation: 0)) == .held(.invalidRequest))
    }
}
