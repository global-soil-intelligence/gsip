// SPDX-License-Identifier: MIT
import XCTest
import Foundation
import Darwin
import CryptoKit
import GSIPStorageCore
@testable import App

/// This helper seeds only the newly owned simulator's fixed synthetic namespace.
/// Protected-data availability is explicitly injected true; this is no lock/device proof.
final class HostOwnedCanaryFixture {
    let identity: SyntheticRunIdentity
    let database: ExcludedSQLiteStore
    let root: URL
    let lease = StorageLease(owner: "synthetic-owner", authEpoch: 0, launch: "synthetic-photo-launch", generation: 0)
    var active = true
    var protectedDataAvailable = true
    var time = ProcessInfo.processInfo.systemUptime
    init() throws {
        let authority = try SyntheticFixtureAuthority.forOwnedSimulator(expectedBundleIdentifier: PrototypeHostController.bundleIdentifier)
        identity = try KeychainAnchor.makeRunIdentity(authority: authority)
        database = try ExcludedSQLiteStore.createSyntheticFixture(authority: authority, identity: identity, owner: "synthetic-owner", protectedDataAvailable: { true })
        guard let library = FileManager.default.urls(for: .libraryDirectory, in: .userDomainMask).first else { throw StorageHold.boundary }
        root = library.appendingPathComponent("GSIPStoragePrototype-v1", isDirectory: true)
            .appendingPathComponent(identity.nonce, isDirectory: true)
    }
    func broker() throws -> OwnedTemporaryPhotoBroker {
        try OwnedTemporaryPhotoBroker(identity: identity, lease: lease,
                                      isCurrent: { [weak self] in self?.active == true },
                                      now: { [weak self] in self?.time ?? .greatestFiniteMagnitude },
                                      protectedDataAvailable: { [weak self] in self?.protectedDataAvailable == true })
    }
}

final class OwnedTemporaryPhotoBrokerTests: XCTestCase {
    func testOnlyNativeMintedCanaryHandleCanReadOwnedProtectedFile() throws {
        let fixture = try HostOwnedCanaryFixture()
        let broker = try fixture.broker()
        let handle = try broker.issueSyntheticCanary()
        XCTAssertTrue(handle.count == 64)
        XCTAssertTrue(broker.contains(handle: handle))
        XCTAssertTrue(try broker.read(handle: handle).count > 0)
        XCTAssertThrowsError(try broker.read(handle: "synthetic-unknown"))
        XCTAssertThrowsError(try broker.read(handle: fixture.root.path))
        let url = fixture.root.appendingPathComponent("gsip-photo-canary.bin")
        var fresh = URL(fileURLWithPath: url.path)
        fresh.removeAllCachedResourceValues()
        let values = try fresh.resourceValues(forKeys: [.fileProtectionKey, .isExcludedFromBackupKey, .isRegularFileKey])
        XCTAssertTrue(values.isExcludedFromBackup == true && values.isRegularFile == true)
        XCTAssertTrue(values.fileProtection == .complete)
    }

    func testExpiryStaleLeaseAndRevocationPreserveBytesButDenyHandles() throws {
        let fixture = try HostOwnedCanaryFixture()
        let broker = try fixture.broker()
        let handle = try broker.issueSyntheticCanary()
        fixture.time += 61
        XCTAssertFalse(broker.contains(handle: handle))
        XCTAssertThrowsError(try broker.read(handle: handle))
        fixture.time -= 61
        fixture.active = false
        XCTAssertThrowsError(try broker.read(handle: handle))
        fixture.active = true
        broker.revoke()
        XCTAssertThrowsError(try broker.read(handle: handle))
        XCTAssertTrue(FileManager.default.fileExists(atPath: fixture.root.appendingPathComponent("gsip-photo-canary.bin").path))
    }

    func testDefaultOrLostProtectedDataAvailabilityHoldsAndPreservesFile() throws {
        let fixture = try HostOwnedCanaryFixture()
        XCTAssertThrowsError(try OwnedTemporaryPhotoBroker(identity: fixture.identity, lease: fixture.lease, isCurrent: { true }))
        let broker = try fixture.broker()
        let handle = try broker.issueSyntheticCanary()
        fixture.protectedDataAvailable = false
        XCTAssertThrowsError(try broker.read(handle: handle))
        XCTAssertThrowsError(try broker.issueSyntheticCanary())
        XCTAssertTrue(FileManager.default.fileExists(atPath: fixture.root.appendingPathComponent("gsip-photo-canary.bin").path))
    }

    func testLoosenedOwnedFilePermissionsHold() throws {
        let fixture = try HostOwnedCanaryFixture()
        let broker = try fixture.broker()
        let handle = try broker.issueSyntheticCanary()
        let url = fixture.root.appendingPathComponent("gsip-photo-canary.bin")
        XCTAssertTrue(chmod(url.path, mode_t(0o644)) == 0)
        XCTAssertThrowsError(try broker.read(handle: handle))
    }

    func testBackwardInjectedClockHoldsRatherThanExtendsExpiry() throws {
        let fixture = try HostOwnedCanaryFixture()
        let broker = try fixture.broker()
        let handle = try broker.issueSyntheticCanary()
        fixture.time -= 1
        XCTAssertThrowsError(try broker.read(handle: handle))
    }

    func testSymlinkOrReplacementCanaryNeverAccepted() throws {
        let fixture = try HostOwnedCanaryFixture()
        let broker = try fixture.broker()
        let handle = try broker.issueSyntheticCanary()
        let url = fixture.root.appendingPathComponent("gsip-photo-canary.bin")
        // Intentional fault under this test's newly owned root, never an app cleanup path.
        XCTAssertTrue(unlink(url.path) == 0)
        XCTAssertTrue(symlink("synthetic-missing-canary", url.path) == 0)
        XCTAssertThrowsError(try broker.read(handle: handle))
        XCTAssertFalse(broker.contains(handle: handle))
    }

    func testRootPolicyLossHoldsAndPreexistingCanaryIsNeverOverwritten() throws {
        let fixture = try HostOwnedCanaryFixture()
        let first = try fixture.broker()
        _ = try first.issueSyntheticCanary()
        let second = try fixture.broker()
        XCTAssertThrowsError(try second.issueSyntheticCanary())
        var root = fixture.root
        var policy = URLResourceValues()
        policy.isExcludedFromBackup = false
        try root.setResourceValues(policy)
        XCTAssertThrowsError(try first.issueSyntheticCanary())
        XCTAssertThrowsError(try fixture.broker())
    }
}
