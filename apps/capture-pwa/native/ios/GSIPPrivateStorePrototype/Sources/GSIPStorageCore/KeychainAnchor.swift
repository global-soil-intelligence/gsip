// SPDX-License-Identifier: MIT
import Foundation
import Security

// Narrow injectable seam, internal to this package's simulator tests. No query is bridge-callable.
protocol PrototypeKeychainCalls: AnyObject {
    func copy(_ query: [String: Any]) -> (OSStatus, [String: Any]?)
    func add(_ attributes: [String: Any]) -> OSStatus
    func update(_ query: [String: Any], attributes: [String: Any]) -> OSStatus
    func random(_ bytes: inout [UInt8]) -> OSStatus
}
private final class PlatformKeychainCalls: PrototypeKeychainCalls {
    func copy(_ query: [String: Any]) -> (OSStatus, [String: Any]?) {
        guard !Thread.isMainThread else { return (errSecInteractionNotAllowed, nil) }
        var result: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        return (status, result as? [String: Any])
    }
    func add(_ attributes: [String: Any]) -> OSStatus {
        guard !Thread.isMainThread else { return errSecInteractionNotAllowed }
        return SecItemAdd(attributes as CFDictionary, nil)
    }
    func update(_ query: [String: Any], attributes: [String: Any]) -> OSStatus {
        guard !Thread.isMainThread else { return errSecInteractionNotAllowed }
        return SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
    }
    func random(_ bytes: inout [UInt8]) -> OSStatus {
        bytes.withUnsafeMutableBytes { pointer in
            guard let base = pointer.baseAddress else { return errSecParam }
            return SecRandomCopyBytes(kSecRandomDefault, pointer.count, base)
        }
    }
}

public final class KeychainAnchor: StorageAnchor {
    public static let service = "com.globalsoilintelligence.app.storageprototype.synthetic.v1"
    private let identity: SyntheticRunIdentity
    private let calls: PrototypeKeychainCalls
    private let expectedDefaultGroup: String?
    private let lock = NSRecursiveLock()
    public convenience init(authority: SyntheticFixtureAuthority, identity: SyntheticRunIdentity) {
        self.init(authority: authority, identity: identity, calls: PlatformKeychainCalls(), expectedDefaultGroup: authority.expectedDefaultAccessGroup)
    }
    init(authority: SyntheticFixtureAuthority, identity: SyntheticRunIdentity, calls: PrototypeKeychainCalls, expectedDefaultGroup: String?) {
        self.identity = identity; self.calls = calls; self.expectedDefaultGroup = expectedDefaultGroup
    }
    public static func makeRunIdentity(authority: SyntheticFixtureAuthority) throws -> SyntheticRunIdentity {
        SyntheticRunIdentity(nonce: try randomNonce(calls: PlatformKeychainCalls()))
    }
    public func freshNonce() throws -> String {
        lock.lock(); defer { lock.unlock() }
        return try Self.randomNonce(calls: calls)
    }
    private static func randomNonce(calls: PrototypeKeychainCalls) throws -> String {
        var bytes = [UInt8](repeating: 0, count: 24)
        guard calls.random(&bytes) == errSecSuccess else { throw StorageHold.unavailable }
        return bytes.map { String(format: "%02x", $0) }.joined()
    }
    private var query: [String: Any] {
        [kSecClass as String: kSecClassGenericPassword,
         kSecAttrService as String: Self.service,
         kSecAttrAccount as String: "anchor-" + identity.nonce,
         kSecAttrSynchronizable as String: false]
    }
    public func read() throws -> AnchorState? {
        lock.lock(); defer { lock.unlock() }
        guard StorageLimits.validIdentifier(identity.nonce) else { throw StorageHold.invalidRequest }
        guard let expectedDefaultGroup, !expectedDefaultGroup.isEmpty, expectedDefaultGroup.utf8.count <= 256 else { throw StorageHold.anchorPolicy }
        var requested = query
        requested[kSecReturnAttributes as String] = true
        requested[kSecReturnData as String] = true
        requested[kSecMatchLimit as String] = kSecMatchLimitOne
        let (status, attributes) = calls.copy(requested)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess else { throw StorageHold.unavailable }
        guard let attributes,
              let accessible = attributes[kSecAttrAccessible as String] as? String,
              accessible == (kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly as String),
              let synchronizable = attributes[kSecAttrSynchronizable as String] as? Bool, !synchronizable,
              let returnedService = attributes[kSecAttrService as String] as? String, returnedService == Self.service,
              let returnedAccount = attributes[kSecAttrAccount as String] as? String,
              returnedAccount == "anchor-" + identity.nonce,
              let defaultGroup = attributes[kSecAttrAccessGroup as String] as? String,
              defaultGroup == expectedDefaultGroup,
              let data = attributes[kSecValueData as String] as? Data,
              data.count > 0, data.count <= 2_048 else { throw StorageHold.anchorPolicy }
        let state: AnchorState
        do { state = try JSONDecoder().decode(AnchorState.self, from: data) }
        catch { throw StorageHold.anchorPolicy }
        guard state.isValid else { throw StorageHold.anchorPolicy }
        return state
    }
    public func update(_ state: AnchorState, expecting: AnchorState) throws {
        lock.lock(); defer { lock.unlock() }
        guard state.isValid, expecting.isValid, state.installation == expecting.installation,
              try read() == expecting else { throw StorageHold.anchorMismatch }
        let legalTransition: Bool
        if expecting.phase == .clean && state.phase == .pending {
            legalTransition = state.revision == expecting.revision && state.nextRevision == expecting.revision + 1 &&
                state.commitNonce != expecting.commitNonce
        } else if expecting.phase == .pending && state.phase == .clean {
            legalTransition = state.revision == expecting.nextRevision && state.commitNonce == expecting.commitNonce
        } else { legalTransition = false }
        guard legalTransition else { throw StorageHold.anchorMismatch }
        let data = try encoded(state)
        let updates: [String: Any] = [kSecValueData as String: data,
                                     kSecAttrAccessible as String: kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly,
                                     kSecAttrSynchronizable as String: false]
        guard calls.update(query, attributes: updates) == errSecSuccess else { throw StorageHold.unavailable }
        guard try read() == state else { throw StorageHold.anchorMismatch }
    }
    /// Explicit fixture seeding only. Absence on ordinary initialization is always held.
    public func seedSyntheticFixture(_ state: AnchorState) throws {
        lock.lock(); defer { lock.unlock() }
        guard state.phase == .clean, state.isValid else { throw StorageHold.invalidRequest }
        guard try read() == nil else { throw StorageHold.operationConflict }
        var attributes = query
        attributes[kSecAttrAccessible as String] = kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly
        attributes[kSecValueData as String] = try encoded(state)
        guard calls.add(attributes) == errSecSuccess else { throw StorageHold.unavailable }
        guard try read() == state else { throw StorageHold.anchorMismatch }
    }
    private func encoded(_ state: AnchorState) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = .sortedKeys
        let data = try encoder.encode(state)
        guard data.count <= 2_048 else { throw StorageHold.invalidRequest }
        return data
    }
}
