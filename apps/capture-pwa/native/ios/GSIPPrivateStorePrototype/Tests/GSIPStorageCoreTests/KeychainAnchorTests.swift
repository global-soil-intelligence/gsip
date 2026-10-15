// SPDX-License-Identifier: MIT
import XCTest
import Foundation
import Security
@testable import GSIPStorageCore

private final class RecordedKeychain: PrototypeKeychainCalls {
    var item: [String: Any]?
    var queries: [[String: Any]] = []
    var adds = 0
    var updates = 0
    var readStatus: OSStatus?
    var updateStatus: OSStatus = errSecSuccess
    var randomStatus: OSStatus = errSecSuccess
    func copy(_ query: [String: Any]) -> (OSStatus, [String: Any]?) {
        queries.append(query)
        if let readStatus { return (readStatus, nil) }
        return item == nil ? (errSecItemNotFound, nil) : (errSecSuccess, item)
    }
    func add(_ attributes: [String: Any]) -> OSStatus {
        adds += 1; item = attributes; item?[kSecAttrAccessGroup as String] = "synthetic-default-group"
        return errSecSuccess
    }
    func update(_ query: [String: Any], attributes: [String: Any]) -> OSStatus {
        queries.append(query); updates += 1
        if updateStatus != errSecSuccess { return updateStatus }
        for (key, value) in attributes { item?[key] = value }
        return errSecSuccess
    }
    func random(_ bytes: inout [UInt8]) -> OSStatus {
        for index in bytes.indices { bytes[index] = UInt8(index) }
        return randomStatus
    }
}

final class KeychainAnchorTests: XCTestCase {
    private func fixture() throws -> (KeychainAnchor, RecordedKeychain) {
        let authority = try requiredSimulatorAuthority()
        let calls = RecordedKeychain()
        return (KeychainAnchor(authority: authority, identity: SyntheticRunIdentity(nonce: "synthetic-native-run"), calls: calls, expectedDefaultGroup: "synthetic-default-group"), calls)
    }
    func testEveryQueryIsExactAndInitialSeedUsesPasscodeBoundClass() throws {
        let (anchor, calls) = try fixture(); let state = AnchorState.clean(syntheticSnapshot())
        try anchor.seedSyntheticFixture(state)
        XCTAssertEqual(calls.adds, 1); XCTAssertEqual(calls.updates, 0)
        for query in calls.queries {
            XCTAssertTrue(query[kSecAttrService as String] as? String == KeychainAnchor.service)
            XCTAssertTrue(query[kSecAttrAccount as String] as? String == "anchor-synthetic-native-run")
            XCTAssertTrue(query[kSecClass as String] as? String == kSecClassGenericPassword as String)
            XCTAssertTrue(query[kSecAttrAccessGroup as String] == nil)
        }
        XCTAssertTrue(calls.item?[kSecAttrAccessible as String] as? String == kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly as String)
        XCTAssertTrue(calls.item?[kSecAttrSynchronizable as String] as? Bool == false)
    }
    func testUpdatesExistingItemWithoutDeleteAddGap() throws {
        let (anchor, calls) = try fixture(); let original = AnchorState.clean(syntheticSnapshot())
        try anchor.seedSyntheticFixture(original)
        let pending = AnchorState(phase: .pending, installation: "synthetic-install", revision: 0,
                                  nextRevision: 1, commitNonce: "next", operationID: "one", operationDigest: String(repeating: "a", count: 64), operationKind: "put")
        try anchor.update(pending, expecting: original)
        XCTAssertEqual(calls.adds, 1); XCTAssertEqual(calls.updates, 1)
        XCTAssertTrue(try anchor.read() == pending)
        XCTAssertThrowsError(try anchor.seedSyntheticFixture(original))
    }
    func testMissingPolicyAttributesAndUnknownStatusesAreHeldNotEmpty() throws {
        let (anchor, calls) = try fixture()
        XCTAssertTrue(try anchor.read() == nil)
        try anchor.seedSyntheticFixture(.clean(syntheticSnapshot()))
        calls.item?.removeValue(forKey: kSecAttrSynchronizable as String)
        XCTAssertThrowsError(try anchor.read()) { XCTAssertTrue($0 as? StorageHold == .anchorPolicy) }
        calls.readStatus = errSecInteractionNotAllowed
        XCTAssertThrowsError(try anchor.read()) { XCTAssertTrue($0 as? StorageHold == .unavailable) }
    }
    func testWeakerClassAndSynchronizableTrueAreRefused() throws {
        let (anchor, calls) = try fixture(); try anchor.seedSyntheticFixture(.clean(syntheticSnapshot()))
        calls.item?[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        XCTAssertThrowsError(try anchor.read())
        calls.item?[kSecAttrAccessible as String] = kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly
        calls.item?[kSecAttrSynchronizable as String] = true
        XCTAssertThrowsError(try anchor.read())
    }
    func testWrongAccessGroupAndUnknownDefaultGroupAreHeld() throws {
        let (anchor, calls) = try fixture(); try anchor.seedSyntheticFixture(.clean(syntheticSnapshot()))
        calls.item?[kSecAttrAccessGroup as String] = "foreign-group"
        XCTAssertThrowsError(try anchor.read()) { XCTAssertTrue($0 as? StorageHold == .anchorPolicy) }
        let authority = try requiredSimulatorAuthority()
        let unknown = KeychainAnchor(authority: authority, identity: SyntheticRunIdentity(nonce: "synthetic-native-run"), calls: calls, expectedDefaultGroup: nil)
        calls.queries = []; calls.adds = 0; calls.updates = 0
        XCTAssertThrowsError(try unknown.read()) { XCTAssertTrue($0 as? StorageHold == .anchorPolicy) }
        XCTAssertThrowsError(try unknown.seedSyntheticFixture(.clean(syntheticSnapshot())))
        XCTAssertEqual(calls.queries.count, 0); XCTAssertEqual(calls.adds, 0); XCTAssertEqual(calls.updates, 0)
    }
    func testAnchorCannotRollbackOrChangeInstallation() throws {
        let (anchor, _) = try fixture(); let state = AnchorState.clean(syntheticSnapshot())
        try anchor.seedSyntheticFixture(state)
        XCTAssertThrowsError(try anchor.update(state, expecting: state))
        let changed = AnchorState(phase: .pending, installation: "foreign-install", revision: 0,
                                  nextRevision: 1, commitNonce: "next", operationID: "one",
                                  operationDigest: String(repeating: "a", count: 64), operationKind: "put")
        XCTAssertThrowsError(try anchor.update(changed, expecting: state))
    }
    func testNonceFailureAndUpdateDenialPropagate() throws {
        let (anchor, calls) = try fixture(); let state = AnchorState.clean(syntheticSnapshot())
        try anchor.seedSyntheticFixture(state); calls.randomStatus = errSecNotAvailable
        XCTAssertThrowsError(try anchor.freshNonce())
        calls.updateStatus = errSecInteractionNotAllowed
        let pending = AnchorState(phase: .pending, installation: "synthetic-install", revision: 0,
                                  nextRevision: 1, commitNonce: "next", operationID: "one",
                                  operationDigest: String(repeating: "a", count: 64), operationKind: "put")
        XCTAssertThrowsError(try anchor.update(pending, expecting: state)) { XCTAssertTrue($0 as? StorageHold == .unavailable) }
        XCTAssertEqual(calls.adds, 1); XCTAssertEqual(calls.updates, 1)
    }
    func testActualPasscodeClassIsAdmittedOrExplicitlyHeldOnSimulator() throws {
        let authority = try requiredSimulatorAuthority()
        let identity = try KeychainAnchor.makeRunIdentity(authority: authority)
        let anchor = KeychainAnchor(authority: authority, identity: identity)
        let snapshot = DatabaseSnapshot(installation: identity.nonce, owner: "synthetic-owner", authEpoch: 0,
                                        revision: 0, generation: 0, commitNonce: identity.nonce)
        let finished = NSCondition()
        var completed = false
        var outcome: StorageHold?
        let queue = OperationQueue(); queue.maxConcurrentOperationCount = 1
        queue.addOperation {
            let result: StorageHold?
            do {
                try anchor.seedSyntheticFixture(.clean(snapshot))
                result = try anchor.read() == .clean(snapshot) ? nil : .anchorMismatch
            } catch { result = (error as? StorageHold) ?? .unavailable }
            finished.lock(); outcome = result; completed = true; finished.signal(); finished.unlock()
        }
        finished.lock()
        let deadline = Date(timeIntervalSinceNow: 5)
        while !completed && finished.wait(until: deadline) { }
        let didFinish = completed; let result = outcome
        finished.unlock()
        guard didFinish else { return XCTFail("bounded anchor probe timeout") }
        if let result {
            XCTAssertTrue([StorageHold.unavailable, .anchorPolicy, .anchorMismatch].contains(result))
            if authority.expectedDefaultAccessGroup == nil { print("GSIP_SIMULATOR_ANCHOR=held-group-unverified") }
            else { print("GSIP_SIMULATOR_ANCHOR=held-api") }
        } else {
            print("GSIP_SIMULATOR_ANCHOR=api-readback")
            // A simulator API readback is not passcode/device/backup certification.
        }
    }
}
