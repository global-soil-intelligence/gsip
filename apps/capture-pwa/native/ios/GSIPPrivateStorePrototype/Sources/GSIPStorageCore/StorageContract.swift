// SPDX-License-Identifier: MIT
import Foundation

/// Synthetic prototype capacities, not a measured memory or durability guarantee.
public enum StorageLimits {
    public static let maxCounter: UInt64 = 9_007_199_254_740_991
    public static let chunkBytes = 131_072
    public static let frameBytes = 524_288
    public static let managedBytes = 268_435_456
    public static func validCounter(_ value: UInt64) -> Bool { value <= maxCounter }
    public static func validIdentifier(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 128 && value.utf8.allSatisfy {
            ($0 >= 48 && $0 <= 57) || ($0 >= 65 && $0 <= 90) ||
            ($0 >= 97 && $0 <= 122) || $0 == 45 || $0 == 95
        }
    }
}

public enum LogicalStore: String, Codable, CaseIterable {
    case submissions, draftPhotos, libraryDraft, libraryNamespace, queueState, syncReminder
    public var isPayload: Bool {
        self == .submissions || self == .draftPhotos || self == .libraryDraft || self == .libraryNamespace
    }
}

public enum StorageHold: String, Error, Codable, Equatable {
    case invalidRequest, staleLease, ownerMismatch, generationMismatch, revisionMismatch
    case exhausted, quota, busy, unavailable, boundary, corrupt, unknownSchema
    case missingDatabase, missingAnchor, anchorPolicy, anchorMismatch, pendingOldDatabase
    case unknownReceipt, operationConflict, interrupted, suspended, unsupportedPlatform
}

public struct StorageLease: Codable, Equatable {
    public let owner: String
    public let authEpoch: UInt64
    public let launch: String
    public let generation: UInt64
    public init(owner: String, authEpoch: UInt64, launch: String, generation: UInt64) {
        self.owner = owner; self.authEpoch = authEpoch; self.launch = launch; self.generation = generation
    }
    public var isValid: Bool {
        StorageLimits.validIdentifier(owner) && StorageLimits.validIdentifier(launch) &&
        StorageLimits.validCounter(authEpoch) && StorageLimits.validCounter(generation)
    }
}

public enum StorageMutation: Codable, Equatable {
    case put(store: LogicalStore, key: String, bytes: Data, expectedRevision: UInt64)
    case remove(store: LogicalStore, key: String, expectedRevision: UInt64)
    case clear
    case beginStage(store: LogicalStore, key: String, length: Int, sha256: String, expectedRevision: UInt64)
    case appendStage(stageID: String, offset: Int, bytes: Data)
    case finishStage(stageID: String)
    public var kind: String {
        switch self {
        case .put: return "put"
        case .remove: return "remove"
        case .clear: return "clear"
        case .beginStage: return "beginStage"
        case .appendStage: return "appendStage"
        case .finishStage: return "finishStage"
        }
    }
}

public struct StorageRequest: Codable, Equatable {
    public let operationID: String
    public let lease: StorageLease
    public let mutation: StorageMutation
    public init(operationID: String, lease: StorageLease, mutation: StorageMutation) {
        self.operationID = operationID; self.lease = lease; self.mutation = mutation
    }
    public var isValid: Bool {
        guard StorageLimits.validIdentifier(operationID), lease.isValid else { return false }
        switch mutation {
        case let .put(store, key, bytes, revision):
            return store.isPayload && StorageLimits.validIdentifier(key) && bytes.count <= StorageLimits.chunkBytes && StorageLimits.validCounter(revision)
        case let .remove(store, key, revision):
            return store.isPayload && StorageLimits.validIdentifier(key) && StorageLimits.validCounter(revision)
        case .clear: return true
        case let .beginStage(store, key, length, sha256, revision):
            return store.isPayload && StorageLimits.validIdentifier(key) && length > 0 &&
                length <= StorageLimits.managedBytes && sha256.count == 64 &&
                sha256.utf8.allSatisfy { ($0 >= 48 && $0 <= 57) || ($0 >= 97 && $0 <= 102) } && StorageLimits.validCounter(revision)
        case let .appendStage(stageID, offset, bytes):
            return StorageLimits.validIdentifier(stageID) && offset >= 0 && offset <= StorageLimits.managedBytes &&
                !bytes.isEmpty && bytes.count <= StorageLimits.chunkBytes
        case let .finishStage(stageID): return StorageLimits.validIdentifier(stageID)
        }
    }
}

public struct DatabaseSnapshot: Codable, Equatable {
    public let schema: UInt64
    public let installation: String
    public let owner: String
    public let authEpoch: UInt64
    public let revision: UInt64
    public let generation: UInt64
    public let commitNonce: String
    public init(schema: UInt64 = 1, installation: String, owner: String, authEpoch: UInt64,
                revision: UInt64, generation: UInt64, commitNonce: String) {
        self.schema = schema; self.installation = installation; self.owner = owner; self.authEpoch = authEpoch
        self.revision = revision; self.generation = generation; self.commitNonce = commitNonce
    }
    public var isValid: Bool {
        schema == 1 && StorageLimits.validIdentifier(installation) && StorageLimits.validIdentifier(owner) &&
        StorageLimits.validIdentifier(commitNonce) && StorageLimits.validCounter(authEpoch) &&
        StorageLimits.validCounter(revision) && StorageLimits.validCounter(generation)
    }
}

public struct StorageAcknowledgement: Codable, Equatable {
    public let operationID: String
    public let revision: UInt64
    public let generation: UInt64
    public let recordRevision: UInt64
    public let retry: Bool
    public init(operationID: String, revision: UInt64, generation: UInt64, recordRevision: UInt64, retry: Bool = false) {
        self.operationID = operationID; self.revision = revision; self.generation = generation
        self.recordRevision = recordRevision; self.retry = retry
    }
}

public struct OperationReceipt: Codable, Equatable {
    public let requestDigest: String
    public let kind: String
    public let lease: StorageLease
    public let commitNonce: String
    public let acknowledgement: StorageAcknowledgement
    public init(requestDigest: String, lease: StorageLease, commitNonce: String, acknowledgement: StorageAcknowledgement, kind: String = "put") {
        self.kind = kind; self.requestDigest = requestDigest; self.lease = lease; self.commitNonce = commitNonce; self.acknowledgement = acknowledgement
    }
}

public struct StorageRecord: Equatable {
    public let bytes: Data
    public let revision: UInt64
    public init(bytes: Data, revision: UInt64) { self.bytes = bytes; self.revision = revision }
}

public enum StorageAdmission: Equatable { case admitted(StorageLease), held(StorageHold) }
public enum StorageResult: Equatable { case acknowledged(StorageAcknowledgement), staged(StorageAcknowledgement), held(StorageHold) }
public enum StorageReadResult: Equatable { case found(StorageRecord), absent, held(StorageHold) }

public enum AnchorPhase: String, Codable { case clean, pending }
public struct AnchorState: Codable, Equatable {
    public let phase: AnchorPhase
    public let installation: String
    public let revision: UInt64
    public let nextRevision: UInt64?
    public let commitNonce: String
    public let operationID: String?
    public let operationDigest: String?
    public let operationKind: String?
    public init(phase: AnchorPhase, installation: String, revision: UInt64, nextRevision: UInt64? = nil,
                commitNonce: String, operationID: String? = nil, operationDigest: String? = nil, operationKind: String? = nil) {
        self.phase = phase; self.installation = installation; self.revision = revision; self.nextRevision = nextRevision
        self.commitNonce = commitNonce; self.operationID = operationID; self.operationDigest = operationDigest; self.operationKind = operationKind
    }
    public static func clean(_ snapshot: DatabaseSnapshot) -> AnchorState {
        AnchorState(phase: .clean, installation: snapshot.installation, revision: snapshot.revision, commitNonce: snapshot.commitNonce)
    }
    public var isValid: Bool {
        guard StorageLimits.validIdentifier(installation), StorageLimits.validIdentifier(commitNonce),
              StorageLimits.validCounter(revision) else { return false }
        if phase == .clean { return nextRevision == nil && operationID == nil && operationDigest == nil && operationKind == nil }
        guard revision < StorageLimits.maxCounter, nextRevision == revision + 1,
              let operationID, StorageLimits.validIdentifier(operationID), let operationDigest,
              operationDigest.count == 64, let operationKind,
              ["put", "remove", "clear", "beginStage", "appendStage", "finishStage"].contains(operationKind) else { return false }
        return operationDigest.utf8.allSatisfy { ($0 >= 48 && $0 <= 57) || ($0 >= 97 && $0 <= 102) }
    }
}

/// Implementations must return held errors, never infer empty state from unknown errors.
public protocol StorageDatabase: AnyObject {
    func validateBoundary() throws
    func snapshot() throws -> DatabaseSnapshot
    func digest(_ request: StorageRequest) throws -> String
    func receipt(operationID: String) throws -> OperationReceipt?
    func prepare(_ request: StorageRequest) throws
    func commit(_ request: StorageRequest, next: DatabaseSnapshot, digest: String) throws -> OperationReceipt
    func read(store: LogicalStore, key: String) throws -> StorageRecord?
}
public protocol StorageAnchor: AnyObject {
    func read() throws -> AnchorState?
    func update(_ state: AnchorState, expecting: AnchorState) throws
    func freshNonce() throws -> String
}

/// An identity is minted only through the Security-backed native synthetic fixture authority.
public struct SyntheticRunIdentity: Equatable {
    public let nonce: String
    init(nonce: String) { self.nonce = nonce }
}

/// Explicitly scoped to a fresh runner-owned simulator. Never expose this type to JavaScript.
public struct SyntheticFixtureAuthority {
    public let bundleIdentifier: String
    let expectedDefaultAccessGroup: String?
    private init(bundleIdentifier: String, expectedDefaultAccessGroup: String?) {
        self.bundleIdentifier = bundleIdentifier; self.expectedDefaultAccessGroup = expectedDefaultAccessGroup
    }
    public static func forOwnedSimulator(expectedBundleIdentifier: String, expectedDefaultAccessGroup: String? = nil) throws -> SyntheticFixtureAuthority {
        #if targetEnvironment(simulator)
        let main = Bundle.main.bundleIdentifier ?? ""
        let environment = ProcessInfo.processInfo.environment
        guard environment["SIMULATOR_UDID"]?.isEmpty == false else { throw StorageHold.unsupportedPlatform }
        let actual: String
        if expectedBundleIdentifier == "com.globalsoilintelligence.app.storageprototype" {
            guard main == expectedBundleIdentifier else { throw StorageHold.unsupportedPlatform }
            actual = main
        } else {
            // Hostless SwiftPM tests run in Apple's xctest tool. Bind the exact loaded test
            // bundle selected from the fresh xctestrun by the independent Python harness.
            let loaded = Bundle.allBundles
            guard environment["GSIP_PROTOTYPE_HOSTLESS_CORE_TESTS"] == "1", loaded.count <= 512,
                  main != "com.globalsoilintelligence.app", expectedBundleIdentifier.contains("GSIPStorageCore"),
                  loaded.filter({ $0.bundleIdentifier == expectedBundleIdentifier }).count == 1 else {
                throw StorageHold.unsupportedPlatform
            }
            actual = expectedBundleIdentifier
        }
        let group = expectedDefaultAccessGroup ?? ProcessInfo.processInfo.environment["GSIP_PROTOTYPE_EXPECTED_ACCESS_GROUP"]
        guard group == nil || (group!.utf8.count > 0 && group!.utf8.count <= 256) else { throw StorageHold.unsupportedPlatform }
        return SyntheticFixtureAuthority(bundleIdentifier: actual, expectedDefaultAccessGroup: group)
        #else
        throw StorageHold.unsupportedPlatform
        #endif
    }
}

/// Bounded platform settings only; contains no private root, record or anchor value.
public struct SQLiteRuntimeEvidence: Equatable {
    public let version: String
    public let sourceID: String
    public let compileOptions: [String]
    public let vfs: String
    public let journalMode: String
    public let synchronous: Int64
    public let foreignKeys: Int64
    public let tempStore: Int64
    public let fullFSyncRequestedReadback: Int64
    public let busyMilliseconds: Int64
    public let attachedLimit: Int32
}
