// SPDX-License-Identifier: MIT
import Foundation
import Darwin
import SQLite3
import CryptoKit

/// Fixed synthetic namespace. One connection and an internal lock preserve serialization even
/// under accidental native re-entry. Ordinary app stores and caller-provided paths are absent.
public final class ExcludedSQLiteStore: StorageDatabase {
    private static let databaseName = "gsip-app2c2a.sqlite3"
    private static let journalName = "gsip-app2c2a.sqlite3-journal"
    private static let registryLock = NSLock()
    private static var openIdentities = Set<String>()
    private let registryNonce: String
    private var writerClaimed = false
    private var receiptConstraintFault = false
    private static let tableSchema: [(String, String)] = [
        ("control", "CREATE TABLE control (id INTEGER PRIMARY KEY CHECK(id=1), value BLOB NOT NULL)"),
        ("records", "CREATE TABLE records (store TEXT NOT NULL, key TEXT NOT NULL, revision INTEGER NOT NULL, payload BLOB NOT NULL, PRIMARY KEY(store,key))"),
        ("receipts", "CREATE TABLE receipts (operation TEXT PRIMARY KEY, value BLOB NOT NULL)"),
        ("staging", "CREATE TABLE staging (operation TEXT PRIMARY KEY, store TEXT NOT NULL, key TEXT NOT NULL, total INTEGER NOT NULL, digest TEXT NOT NULL, expected INTEGER NOT NULL, lease BLOB NOT NULL, payload BLOB NOT NULL)"),
        ("reminder", "CREATE TABLE reminder (id INTEGER PRIMARY KEY CHECK(id=1), generation INTEGER NOT NULL, revision INTEGER NOT NULL, enabled INTEGER NOT NULL CHECK(enabled=0), cleanup_pending INTEGER NOT NULL CHECK(cleanup_pending=1))")
    ]
    private let root: URL
    private let protectedDataAvailable: () -> Bool
    private let rootDescriptor: Int32
    private let databaseDescriptor: Int32
    private let rootIdentity: FileIdentity
    private let databaseIdentity: FileIdentity
    private let lock = NSRecursiveLock()
    private var connection: OpaquePointer?
    private var closed = false
    private let transient = unsafeBitCast(-1, to: sqlite3_destructor_type.self)
    private struct FileIdentity: Equatable { let device: UInt64; let inode: UInt64 }

    public static func createSyntheticFixture(authority: SyntheticFixtureAuthority, identity: SyntheticRunIdentity,
                                              owner: String, protectedDataAvailable: @escaping () -> Bool = { false }) throws -> ExcludedSQLiteStore {
        guard protectedDataAvailable() else { throw StorageHold.unavailable }
        guard StorageLimits.validIdentifier(identity.nonce), StorageLimits.validIdentifier(owner) else { throw StorageHold.invalidRequest }
        let root = try rootURL(identity)
        let base = root.deletingLastPathComponent()
        if !FileManager.default.fileExists(atPath: base.path) {
            try FileManager.default.createDirectory(at: base, withIntermediateDirectories: false,
                                                    attributes: [.posixPermissions: 0o700, .protectionKey: FileProtectionType.complete])
            try applyPolicy(base)
        }
        _ = try checkedFile(base, directory: true)
        guard !FileManager.default.fileExists(atPath: root.path) else { throw StorageHold.operationConflict }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false,
                                                attributes: [.posixPermissions: 0o700, .protectionKey: FileProtectionType.complete])
        try applyPolicy(root)
        _ = try checkedFile(root, directory: true)
        let databaseURL = root.appendingPathComponent(databaseName, isDirectory: false)
        let descriptor = Darwin.open(databaseURL.path, O_RDWR | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0o600)
        guard descriptor >= 0 else { throw StorageHold.boundary }
        Darwin.close(descriptor)
        try applyPolicy(databaseURL)
        let store = try ExcludedSQLiteStore(authority: authority, identity: identity, protectedDataAvailable: protectedDataAvailable, allowEmptyFixture: true)
        let initial = DatabaseSnapshot(installation: identity.nonce, owner: owner, authEpoch: 0,
                                       revision: 0, generation: 0, commitNonce: identity.nonce)
        try store.createSchema(initial)
        return store
    }

    public convenience init(authority: SyntheticFixtureAuthority, identity: SyntheticRunIdentity,
                            protectedDataAvailable: @escaping () -> Bool = { false }) throws {
        try self.init(authority: authority, identity: identity, protectedDataAvailable: protectedDataAvailable, allowEmptyFixture: false)
    }
    private init(authority: SyntheticFixtureAuthority, identity: SyntheticRunIdentity,
                 protectedDataAvailable: @escaping () -> Bool, allowEmptyFixture: Bool) throws {
        guard protectedDataAvailable() else { throw StorageHold.unavailable }
        self.protectedDataAvailable = protectedDataAvailable
        self.registryNonce = identity.nonce
        self.root = try Self.rootURL(identity)
        rootIdentity = try Self.checkedFile(root, directory: true)
        rootDescriptor = Darwin.open(root.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard rootDescriptor >= 0 else { throw StorageHold.boundary }
        let databaseURL = root.appendingPathComponent(Self.databaseName)
        do { databaseIdentity = try Self.checkedFile(databaseURL, directory: false) }
        catch { Darwin.close(rootDescriptor); throw error }
        databaseDescriptor = Darwin.open(databaseURL.path, O_RDWR | O_NOFOLLOW | O_CLOEXEC)
        guard databaseDescriptor >= 0 else { Darwin.close(rootDescriptor); throw StorageHold.boundary }
        Self.registryLock.lock()
        let unique = Self.openIdentities.insert(identity.nonce).inserted
        Self.registryLock.unlock()
        guard unique else { Darwin.close(databaseDescriptor); Darwin.close(rootDescriptor); closed = true; throw StorageHold.busy }
        do {
            try validateBoundary()
            if !allowEmptyFixture {
                var readonly: OpaquePointer?
                let observed = sqlite3_open_v2(databaseURL.path, &readonly, SQLITE_OPEN_READONLY | SQLITE_OPEN_FULLMUTEX, nil)
                connection = readonly
                guard observed == SQLITE_OK, readonly != nil else { throw sqliteHold(observed) }
                // Unknown same-version schema is inspected read-only before any mode change.
                _ = try snapshot()
                guard sqlite3_close_v2(readonly) == SQLITE_OK else { throw StorageHold.interrupted }
                connection = nil
                try validateBoundary()
            }
            var pointer: OpaquePointer?
            let result = sqlite3_open_v2(databaseURL.path, &pointer,
                                         SQLITE_OPEN_READWRITE | SQLITE_OPEN_FULLMUTEX, nil)
            connection = pointer
            guard result == SQLITE_OK, pointer != nil else { throw sqliteHold(result) }
            sqlite3_extended_result_codes(pointer, 1)
            guard sqlite3_busy_timeout(pointer, 250) == SQLITE_OK else { throw StorageHold.unavailable }
            _ = sqlite3_limit(pointer, SQLITE_LIMIT_LENGTH, Int32(StorageLimits.managedBytes))
            _ = sqlite3_limit(pointer, SQLITE_LIMIT_SQL_LENGTH, 16_384)
            _ = sqlite3_limit(pointer, SQLITE_LIMIT_COLUMN, 32)
            _ = sqlite3_limit(pointer, SQLITE_LIMIT_ATTACHED, 0)
            _ = sqlite3_limit(pointer, SQLITE_LIMIT_COMPOUND_SELECT, 4)
            _ = sqlite3_limit(pointer, SQLITE_LIMIT_VARIABLE_NUMBER, 16)
            try executeFixed("PRAGMA journal_mode=DELETE")
            try executeFixed("PRAGMA synchronous=EXTRA")
            try executeFixed("PRAGMA foreign_keys=ON")
            try executeFixed("PRAGMA temp_store=MEMORY")
            try executeFixed("PRAGMA fullfsync=ON")
            guard try scalarText("PRAGMA journal_mode") == "delete",
                  try scalarInteger("PRAGMA synchronous") == 3,
                  try scalarInteger("PRAGMA foreign_keys") == 1,
                  try scalarInteger("PRAGMA temp_store") == 2 else { throw StorageHold.unavailable }
            // Readback is recorded as a request only; it is not power-loss proof.
            _ = try scalarInteger("PRAGMA fullfsync")
            try validateBoundary()
            if !allowEmptyFixture { _ = try snapshot() }
        } catch {
            if let connection { sqlite3_close_v2(connection); self.connection = nil }
            Darwin.close(databaseDescriptor); Darwin.close(rootDescriptor); closed = true
            Self.releaseIdentity(registryNonce)
            throw error
        }
    }
    deinit {
        if let connection { sqlite3_close_v2(connection) }
        if !closed { Darwin.close(databaseDescriptor); Darwin.close(rootDescriptor); Self.releaseIdentity(registryNonce) }
    }
    private static func releaseIdentity(_ nonce: String) {
        registryLock.lock(); defer { registryLock.unlock() }; openIdentities.remove(nonce)
    }
    func claimWriter() -> Bool {
        lock.lock(); defer { lock.unlock() }
        guard !writerClaimed else { return false }
        writerClaimed = true; return true
    }
    func releaseWriter() { lock.lock(); defer { lock.unlock() }; writerClaimed = false }

    private static func rootURL(_ identity: SyntheticRunIdentity) throws -> URL {
        guard StorageLimits.validIdentifier(identity.nonce),
              let library = FileManager.default.urls(for: .libraryDirectory, in: .userDomainMask).first else { throw StorageHold.boundary }
        let resolved = library.resolvingSymlinksInPath().standardizedFileURL
        return resolved.appendingPathComponent("GSIPStoragePrototype-v1", isDirectory: true)
            .appendingPathComponent(identity.nonce, isDirectory: true)
    }
    private static func applyPolicy(_ url: URL) throws {
        // The public URL resource API supplies actual complete-protection readback on the
        // simulator; FileManager's attributes dictionary can omit its protection key.
        try (url as NSURL).setResourceValue(URLFileProtection.complete.rawValue, forKey: .fileProtectionKey)
        var mutableURL = url
        var values = URLResourceValues(); values.isExcludedFromBackup = true
        try mutableURL.setResourceValues(values)
        _ = try checkedFile(url, directory: false, eitherKind: true)
    }
    private static func checkedFile(_ url: URL, directory: Bool, eitherKind: Bool = false) throws -> FileIdentity {
        var info = stat()
        guard lstat(url.path, &info) == 0 else { throw StorageHold.boundary }
        let kind = info.st_mode & S_IFMT
        guard kind != S_IFLNK, kind == S_IFREG || kind == S_IFDIR,
              eitherKind || (directory ? kind == S_IFDIR : kind == S_IFREG),
              info.st_uid == geteuid(), (kind != S_IFREG || info.st_nlink == 1),
              info.st_size >= 0, UInt64(info.st_size) <= UInt64(StorageLimits.managedBytes),
              info.st_mode & 0o077 == 0 else { throw StorageHold.boundary }
        var freshURL = URL(fileURLWithPath: url.path)
        freshURL.removeAllCachedResourceValues()
        let values = try freshURL.resourceValues(forKeys: [.fileProtectionKey, .isExcludedFromBackupKey])
        guard values.fileProtection == .complete, values.isExcludedFromBackup == true else { throw StorageHold.boundary }
        return FileIdentity(device: UInt64(info.st_dev), inode: UInt64(info.st_ino))
    }
    private func descriptorIdentity(_ descriptor: Int32) throws -> FileIdentity {
        var info = stat()
        guard fstat(descriptor, &info) == 0 else { throw StorageHold.boundary }
        return FileIdentity(device: UInt64(info.st_dev), inode: UInt64(info.st_ino))
    }
    public func validateBoundary() throws {
        lock.lock(); defer { lock.unlock() }
        guard protectedDataAvailable() else { throw StorageHold.unavailable }
        guard try Self.checkedFile(root.deletingLastPathComponent(), directory: true) ==
                Self.checkedFile(root.deletingLastPathComponent().resolvingSymlinksInPath(), directory: true),
              try Self.checkedFile(root, directory: true) == rootIdentity,
              try descriptorIdentity(rootDescriptor) == rootIdentity,
              try Self.checkedFile(root.appendingPathComponent(Self.databaseName), directory: false) == databaseIdentity,
              try descriptorIdentity(databaseDescriptor) == databaseIdentity else { throw StorageHold.boundary }
        let names = try FileManager.default.contentsOfDirectory(atPath: root.path)
        guard names.count <= 3, Set(names).isSubset(of: [Self.databaseName, Self.journalName, "gsip-photo-canary.bin"]) else { throw StorageHold.boundary }
        var bytes: UInt64 = 0
        for name in names {
            let url = root.appendingPathComponent(name)
            _ = try Self.checkedFile(url, directory: false)
            var info = stat(); guard lstat(url.path, &info) == 0 else { throw StorageHold.boundary }
            bytes += UInt64(info.st_size)
        }
        guard bytes <= UInt64(StorageLimits.managedBytes) else { throw StorageHold.quota }
    }
    private func provisionJournal() throws -> FileIdentity {
        let url = root.appendingPathComponent(Self.journalName)
        if !FileManager.default.fileExists(atPath: url.path) {
            let descriptor = Darwin.open(url.path, O_RDWR | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0o600)
            guard descriptor >= 0 else { throw StorageHold.boundary }
            Darwin.close(descriptor)
            try Self.applyPolicy(url)
        }
        // An existing journal is admitted, never manually removed; SQLite owns recovery.
        return try Self.checkedFile(url, directory: false)
    }
    private func transaction<T>(_ body: () throws -> T) throws -> T {
        try validateBoundary()
        let journal = try provisionJournal()
        try executeFixed("BEGIN IMMEDIATE")
        do {
            let result = try body()
            let url = root.appendingPathComponent(Self.journalName)
            guard try Self.checkedFile(url, directory: false) == journal else { throw StorageHold.boundary }
            try validateBoundary()
            try executeFixed("COMMIT")
            try validateBoundary()
            return result
        } catch {
            // OR ROLLBACK may already have aborted the transaction. Never mask that original
            // bounded error with a second ROLLBACK error, or manually delete a hot journal.
            if sqlite3_get_autocommit(connection) == 0 {
                do { try executeFixed("ROLLBACK") } catch { throw StorageHold.interrupted }
            }
            throw error
        }
    }
    private func createSchema(_ initial: DatabaseSnapshot) throws {
        lock.lock(); defer { lock.unlock() }
        try transaction {
            for (_, sql) in Self.tableSchema { try executeFixed(sql) }
            try bound("INSERT OR ROLLBACK INTO control(id,value) VALUES(1,?)", blobs: [try encoded(initial)])
            try bound("INSERT OR ROLLBACK INTO reminder VALUES(1,0,0,0,1)")
            try executeFixed("PRAGMA user_version=1")
        }
    }
    public func snapshot() throws -> DatabaseSnapshot {
        lock.lock(); defer { lock.unlock() }
        try validateBoundary()
        guard try scalarInteger("PRAGMA user_version") == 1 else { throw StorageHold.unknownSchema }
        try validateSchema()
        let bytes = try oneBlob("SELECT value FROM control WHERE id=1", strings: [])
        guard let bytes, bytes.count <= 2_048 else { throw StorageHold.corrupt }
        let snapshot: DatabaseSnapshot = try decoded(bytes)
        guard snapshot.isValid else { throw StorageHold.corrupt }
        guard try scalarInteger("SELECT COUNT(*) FROM control") == 1,
              try scalarInteger("SELECT COUNT(*) FROM reminder") == 1,
              try scalarInteger("SELECT enabled FROM reminder WHERE id=1") == 0,
              try scalarInteger("SELECT cleanup_pending FROM reminder WHERE id=1") == 1,
              try scalarInteger("SELECT generation FROM reminder WHERE id=1") == Int64(snapshot.generation),
              try scalarInteger("SELECT revision FROM reminder WHERE id=1") == Int64(snapshot.revision),
              try scalarInteger("SELECT COALESCE(MAX(revision),0) FROM records") <= Int64(snapshot.revision),
              try scalarInteger("SELECT COUNT(*) FROM records WHERE store NOT IN ('submissions','draftPhotos','libraryDraft','libraryNamespace') OR length(key)=0 OR length(key)>128 OR key GLOB '*[^A-Za-z0-9_-]*' OR revision<=0 OR revision>9007199254740991 OR typeof(payload)!='blob'") == 0 else { throw StorageHold.corrupt }
        return snapshot
    }
    private func validateSchema() throws {
        var expected = Dictionary(uniqueKeysWithValues: Self.tableSchema)
        var indexes: [String: String] = ["sqlite_autoindex_records_1": "records", "sqlite_autoindex_receipts_1": "receipts", "sqlite_autoindex_staging_1": "staging"]
        try withStatement("SELECT type,name,tbl_name,sql FROM sqlite_master") { statement in
            var count = 0
            while true {
                let code = sqlite3_step(statement)
                if code == SQLITE_DONE { break }
                guard code == SQLITE_ROW else { throw sqliteHold(code) }
                count += 1
                guard count <= 8, let typePointer = sqlite3_column_text(statement, 0),
                      let namePointer = sqlite3_column_text(statement, 1),
                      let tablePointer = sqlite3_column_text(statement, 2) else { throw StorageHold.unknownSchema }
                let type = String(cString: typePointer), name = String(cString: namePointer), table = String(cString: tablePointer)
                guard type.utf8.count <= 16, name.utf8.count <= 128, table.utf8.count <= 128 else { throw StorageHold.unknownSchema }
                if type == "table" {
                    guard name == table, let exact = expected.removeValue(forKey: name),
                          let sqlPointer = sqlite3_column_text(statement, 3), String(cString: sqlPointer) == exact else { throw StorageHold.unknownSchema }
                } else if type == "index" {
                    guard indexes.removeValue(forKey: name) == table, sqlite3_column_type(statement, 3) == SQLITE_NULL else { throw StorageHold.unknownSchema }
                } else { throw StorageHold.unknownSchema }
            }
            guard expected.isEmpty, indexes.isEmpty else { throw StorageHold.unknownSchema }
        }
    }
    // Native test-only fixed fault; never exposed by the host/plugin or ordinary artifacts.
    func injectReceiptConstraintFaultForSyntheticTest() {
        lock.lock(); defer { lock.unlock() }; receiptConstraintFault = true
    }
    public func runtimeEvidence() throws -> SQLiteRuntimeEvidence {
        lock.lock(); defer { lock.unlock() }
        try validateBoundary()
        var options: [String] = []
        for index in 0..<256 {
            guard let option = sqlite3_compileoption_get(Int32(index)) else { break }
            let value = String(cString: option)
            guard value.utf8.count <= 256 else { throw StorageHold.unavailable }
            options.append(value)
        }
        var vfsPointer: UnsafeMutablePointer<CChar>?
        let code = sqlite3_file_control(connection, "main", SQLITE_FCNTL_VFSNAME, &vfsPointer)
        let vfs: String
        if code == SQLITE_OK, let vfsPointer {
            defer { sqlite3_free(vfsPointer) }
            vfs = String(cString: vfsPointer)
        } else { vfs = "unavailable" }
        guard vfs.utf8.count <= 256 else { throw StorageHold.unavailable }
        return SQLiteRuntimeEvidence(version: String(cString: sqlite3_libversion()),
                                     sourceID: String(cString: sqlite3_sourceid()), compileOptions: options, vfs: vfs,
                                     journalMode: try scalarText("PRAGMA journal_mode"),
                                     synchronous: try scalarInteger("PRAGMA synchronous"),
                                     foreignKeys: try scalarInteger("PRAGMA foreign_keys"),
                                     tempStore: try scalarInteger("PRAGMA temp_store"),
                                     fullFSyncRequestedReadback: try scalarInteger("PRAGMA fullfsync"),
                                     busyMilliseconds: try scalarInteger("PRAGMA busy_timeout"),
                                     attachedLimit: sqlite3_limit(connection, SQLITE_LIMIT_ATTACHED, -1))
    }
    public func digest(_ request: StorageRequest) throws -> String {
        guard request.isValid else { throw StorageHold.invalidRequest }
        return Self.sha256(try encoded(request))
    }
    private static func sha256(_ bytes: Data) -> String { SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined() }
    public func receipt(operationID: String) throws -> OperationReceipt? {
        lock.lock(); defer { lock.unlock() }
        guard StorageLimits.validIdentifier(operationID) else { throw StorageHold.invalidRequest }
        guard let bytes = try oneBlob("SELECT value FROM receipts WHERE operation=?", strings: [operationID]) else { return nil }
        guard bytes.count <= 4_096 else { throw StorageHold.corrupt }
        let receipt: OperationReceipt = try decoded(bytes)
        guard receipt.acknowledgement.operationID == operationID,
              StorageLimits.validCounter(receipt.acknowledgement.revision),
              StorageLimits.validCounter(receipt.acknowledgement.generation),
              StorageLimits.validCounter(receipt.acknowledgement.recordRevision), receipt.lease.isValid,
              StorageLimits.validIdentifier(receipt.commitNonce), receipt.requestDigest.count == 64,
              receipt.requestDigest.utf8.allSatisfy({ ($0 >= 48 && $0 <= 57) || ($0 >= 97 && $0 <= 102) }),
              ["put", "remove", "clear", "beginStage", "appendStage", "finishStage"].contains(receipt.kind) else { throw StorageHold.corrupt }
        return receipt
    }
    public func read(store: LogicalStore, key: String) throws -> StorageRecord? {
        lock.lock(); defer { lock.unlock() }
        guard store.isPayload, StorageLimits.validIdentifier(key) else { throw StorageHold.invalidRequest }
        return try withStatement("SELECT revision,payload FROM records WHERE store=? AND key=?", strings: [store.rawValue, key]) { statement in
            let code = sqlite3_step(statement)
            if code == SQLITE_DONE { return nil }
            guard code == SQLITE_ROW else { throw sqliteHold(code) }
            let revision = sqlite3_column_int64(statement, 0)
            let count = sqlite3_column_bytes(statement, 1)
            guard revision > 0, UInt64(revision) <= StorageLimits.maxCounter, count >= 0,
                  count <= StorageLimits.managedBytes else { throw StorageHold.corrupt }
            let bytes: Data
            if count == 0 { bytes = Data() }
            else {
                guard let pointer = sqlite3_column_blob(statement, 1) else { throw StorageHold.corrupt }
                bytes = Data(bytes: pointer, count: Int(count))
            }
            guard sqlite3_step(statement) == SQLITE_DONE else { throw StorageHold.corrupt }
            return StorageRecord(bytes: bytes, revision: UInt64(revision))
        }
    }
    public func prepare(_ request: StorageRequest) throws {
        lock.lock(); defer { lock.unlock() }
        guard request.isValid else { throw StorageHold.invalidRequest }
        try validateBoundary()
        let snapshot = try snapshot()
        guard request.lease.owner == snapshot.owner, request.lease.authEpoch == snapshot.authEpoch,
              request.lease.generation == snapshot.generation else { throw StorageHold.staleLease }
        switch request.mutation {
        case let .put(store, key, bytes, expected):
            try expectRecord(store, key, expected)
            try reserve(bytes.count + 16_384)
        case let .remove(store, key, expected):
            guard let record = try read(store: store, key: key), record.revision == expected else { throw StorageHold.revisionMismatch }
            try reserve(16_384)
        case .clear:
            guard snapshot.generation < StorageLimits.maxCounter else { throw StorageHold.exhausted }
            try reserve(16_384)
        case let .beginStage(store, key, length, _, expected):
            try expectRecord(store, key, expected)
            guard try oneBlob("SELECT lease FROM staging WHERE operation=?", strings: [request.operationID]) == nil else { throw StorageHold.operationConflict }
            try reserve(length + 16_384)
        case let .appendStage(stageID, offset, bytes):
            let stage = try stage(stageID, lease: request.lease)
            guard stage.payload.count == offset, offset <= stage.total - bytes.count else { throw StorageHold.invalidRequest }
            try reserve(bytes.count + 16_384)
        case let .finishStage(stageID):
            let stage = try stage(stageID, lease: request.lease)
            guard stage.payload.count == stage.total, Self.sha256(stage.payload) == stage.digest else { throw StorageHold.invalidRequest }
            try expectRecord(stage.store, stage.key, stage.expected)
            try reserve(stage.payload.count + 16_384)
        }
    }
    private func expectRecord(_ store: LogicalStore, _ key: String, _ expected: UInt64) throws {
        let current = try read(store: store, key: key)?.revision ?? 0
        guard current == expected else { throw StorageHold.revisionMismatch }
        guard current < StorageLimits.maxCounter else { throw StorageHold.exhausted }
    }
    private func reserve(_ incoming: Int) throws {
        let pages = try scalarInteger("PRAGMA page_count")
        let pageSize = try scalarInteger("PRAGMA page_size")
        guard pages >= 0, pageSize > 0, pages <= Int64(StorageLimits.managedBytes) / pageSize else { throw StorageHold.quota }
        let allocated = pages * pageSize
        let staged = try scalarInteger("SELECT COALESCE(SUM(total),0) FROM staging")
        guard incoming >= 0, staged >= 0,
              allocated <= Int64(StorageLimits.managedBytes) / 2,
              Int64(incoming) <= Int64(StorageLimits.managedBytes) - allocated * 2 - staged else { throw StorageHold.quota }
        let capacity = try root.resourceValues(forKeys: [.volumeAvailableCapacityKey]).volumeAvailableCapacity
        guard let capacity, capacity >= incoming + Int(allocated) + 1_048_576 else { throw StorageHold.quota }
    }
    public func commit(_ request: StorageRequest, next: DatabaseSnapshot, digest: String) throws -> OperationReceipt {
        lock.lock(); defer { lock.unlock() }
        try prepare(request)
        let previous = try snapshot()
        guard next.isValid, next.installation == previous.installation, next.owner == previous.owner,
              next.authEpoch == previous.authEpoch, next.commitNonce != previous.commitNonce, previous.revision < StorageLimits.maxCounter,
              next.revision == previous.revision + 1, digest == (try self.digest(request)),
              try receipt(operationID: request.operationID) == nil else { throw StorageHold.operationConflict }
        return try transaction {
            var recordRevision: UInt64 = 0
            switch request.mutation {
            case let .put(store, key, bytes, expected):
                recordRevision = next.revision
                try writeRecord(store, key, bytes, recordRevision, expected: expected)
            case let .remove(store, key, expected):
                try bound("DELETE FROM records WHERE store=? AND key=? AND revision=?", strings: [store.rawValue, key], integers: [Int64(expected)])
                guard sqlite3_changes(connection) == 1 else { throw StorageHold.revisionMismatch }
            case .clear:
                guard previous.generation < StorageLimits.maxCounter, next.generation == previous.generation + 1 else { throw StorageHold.generationMismatch }
                try executeFixed("DELETE FROM records")
                try executeFixed("DELETE FROM staging")
            case let .beginStage(store, key, total, digest, expected):
                try bound("INSERT OR ROLLBACK INTO staging(operation,store,key,total,digest,expected,lease,payload) VALUES(?,?,?,?,?,?,?,?)",
                          strings: [request.operationID, store.rawValue, key], integers: [Int64(total)],
                          trailingStrings: [digest], trailingIntegers: [Int64(expected)], blobs: [try encoded(request.lease), Data()])
            case let .appendStage(stageID, _, bytes):
                let stage = try stage(stageID, lease: request.lease)
                var joined = stage.payload; joined.append(bytes)
                try bound("UPDATE OR ROLLBACK staging SET payload=? WHERE operation=?", blobs: [joined], endStrings: [stageID])
            case let .finishStage(stageID):
                let stage = try stage(stageID, lease: request.lease)
                recordRevision = next.revision
                try writeRecord(stage.store, stage.key, stage.payload, recordRevision, expected: stage.expected)
                try bound("DELETE FROM staging WHERE operation=?", strings: [stageID])
            }
            if case .clear = request.mutation { }
            else { guard next.generation == previous.generation else { throw StorageHold.generationMismatch } }
            try bound("UPDATE OR ROLLBACK control SET value=? WHERE id=1", blobs: [try encoded(next)])
            try bound("UPDATE OR ROLLBACK reminder SET generation=?, revision=?, enabled=0, cleanup_pending=1 WHERE id=1",
                      integers: [Int64(next.generation), Int64(next.revision)])
            let acknowledgement = StorageAcknowledgement(operationID: request.operationID, revision: next.revision,
                                                          generation: next.generation, recordRevision: recordRevision)
            let receipt = OperationReceipt(requestDigest: digest, lease: request.lease, commitNonce: next.commitNonce, acknowledgement: acknowledgement, kind: request.mutation.kind)
            if receiptConstraintFault {
                receiptConstraintFault = false
                try bound("INSERT OR ROLLBACK INTO receipts(operation,value) VALUES(?,?)", strings: [request.operationID], blobs: [try encoded(receipt)])
            }
            try bound("INSERT OR ROLLBACK INTO receipts(operation,value) VALUES(?,?)", strings: [request.operationID], blobs: [try encoded(receipt)])
            guard sqlite3_changes(connection) == 1 else { throw StorageHold.corrupt }
            return receipt
        }
    }
    private func writeRecord(_ store: LogicalStore, _ key: String, _ bytes: Data, _ revision: UInt64, expected: UInt64) throws {
        if expected == 0 {
            try bound("INSERT OR ROLLBACK INTO records(store,key,revision,payload) VALUES(?,?,?,?)",
                      strings: [store.rawValue, key], integers: [Int64(revision)], blobs: [bytes])
        } else {
            try bound("UPDATE OR ROLLBACK records SET store=?,key=?,revision=?,payload=? WHERE store=? AND key=? AND revision=?",
                      strings: [store.rawValue, key], integers: [Int64(revision)], blobs: [bytes],
                      endStrings: [store.rawValue, key], endIntegers: [Int64(expected)])
        }
        guard sqlite3_changes(connection) == 1 else { throw StorageHold.revisionMismatch }
    }
    private struct Stage {
        let store: LogicalStore; let key: String; let total: Int; let digest: String
        let expected: UInt64; let payload: Data
    }
    private func stage(_ identifier: String, lease: StorageLease) throws -> Stage {
        try withStatement("SELECT store,key,total,digest,expected,lease,payload FROM staging WHERE operation=?", strings: [identifier]) { statement in
            guard sqlite3_step(statement) == SQLITE_ROW,
                  let storePointer = sqlite3_column_text(statement, 0),
                  let store = LogicalStore(rawValue: String(cString: storePointer)), store.isPayload,
                  let keyPointer = sqlite3_column_text(statement, 1),
                  let digestPointer = sqlite3_column_text(statement, 3) else { throw StorageHold.invalidRequest }
            let total = sqlite3_column_int64(statement, 2)
            let expected = sqlite3_column_int64(statement, 4)
            let leaseBytes = try columnBlob(statement, 5)
            let savedLease: StorageLease = try decoded(leaseBytes)
            let payload = try columnBlob(statement, 6)
            guard savedLease == lease, total > 0, total <= StorageLimits.managedBytes,
                  expected >= 0, UInt64(expected) < StorageLimits.maxCounter,
                  payload.count <= Int(total) else { throw StorageHold.staleLease }
            let result = Stage(store: store, key: String(cString: keyPointer), total: Int(total),
                               digest: String(cString: digestPointer), expected: UInt64(expected), payload: payload)
            guard StorageLimits.validIdentifier(result.key), result.digest.count == 64,
                  sqlite3_step(statement) == SQLITE_DONE else { throw StorageHold.corrupt }
            return result
        }
    }
    private func columnBlob(_ statement: OpaquePointer, _ index: Int32) throws -> Data {
        let count = sqlite3_column_bytes(statement, index)
        guard count >= 0, count <= StorageLimits.managedBytes else { throw StorageHold.corrupt }
        if count == 0 { return Data() }
        guard let pointer = sqlite3_column_blob(statement, index) else { throw StorageHold.corrupt }
        return Data(bytes: pointer, count: Int(count))
    }
    private func encoded<T: Encodable>(_ value: T) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = .sortedKeys
        return try encoder.encode(value)
    }
    private func decoded<T: Decodable>(_ bytes: Data) throws -> T {
        do { return try JSONDecoder().decode(T.self, from: bytes) } catch { throw StorageHold.corrupt }
    }
    private func sqliteHold(_ code: Int32) -> StorageHold {
        switch code & 0xff {
        case SQLITE_BUSY, SQLITE_LOCKED: return .busy
        case SQLITE_FULL, SQLITE_TOOBIG: return .quota
        case SQLITE_CORRUPT, SQLITE_NOTADB: return .corrupt
        default: return .unavailable
        }
    }
    private func executeFixed(_ sql: String) throws {
        guard sqlite3_exec(connection, sql, nil, nil, nil) == SQLITE_OK else { throw sqliteHold(sqlite3_errcode(connection)) }
    }
    private func withStatement<T>(_ sql: String, strings: [String] = [], _ body: (OpaquePointer) throws -> T) throws -> T {
        var pointer: OpaquePointer?
        guard sqlite3_prepare_v2(connection, sql, -1, &pointer, nil) == SQLITE_OK, let pointer else { throw sqliteHold(sqlite3_errcode(connection)) }
        defer { sqlite3_finalize(pointer) }
        for (index, value) in strings.enumerated() {
            guard sqlite3_bind_text(pointer, Int32(index + 1), value, -1, transient) == SQLITE_OK else { throw StorageHold.invalidRequest }
        }
        return try body(pointer)
    }
    private func bound(_ sql: String, strings: [String] = [], integers: [Int64] = [],
                       trailingStrings: [String] = [], trailingIntegers: [Int64] = [],
                       blobs: [Data] = [], endStrings: [String] = [], endIntegers: [Int64] = []) throws {
        try withStatement(sql) { statement in
            var index: Int32 = 1
            func texts(_ values: [String]) throws {
                for value in values {
                    guard sqlite3_bind_text(statement, index, value, -1, transient) == SQLITE_OK else { throw StorageHold.invalidRequest }
                    index += 1
                }
            }
            func numbers(_ values: [Int64]) throws {
                for value in values {
                    guard sqlite3_bind_int64(statement, index, value) == SQLITE_OK else { throw StorageHold.invalidRequest }
                    index += 1
                }
            }
            try texts(strings); try numbers(integers); try texts(trailingStrings); try numbers(trailingIntegers)
            for value in blobs {
                let result: Int32
                if value.isEmpty { result = sqlite3_bind_zeroblob(statement, index, 0) }
                else { result = value.withUnsafeBytes { sqlite3_bind_blob(statement, index, $0.baseAddress, Int32(value.count), transient) } }
                guard result == SQLITE_OK else { throw StorageHold.invalidRequest }; index += 1
            }
            try texts(endStrings); try numbers(endIntegers)
            let result = sqlite3_step(statement)
            guard result == SQLITE_DONE else { throw sqliteHold(result) }
        }
    }
    private func scalarInteger(_ sql: String) throws -> Int64 {
        try withStatement(sql) { statement in
            let code = sqlite3_step(statement)
            guard code == SQLITE_ROW else { throw code == SQLITE_DONE ? StorageHold.corrupt : sqliteHold(code) }
            let value = sqlite3_column_int64(statement, 0)
            guard sqlite3_step(statement) == SQLITE_DONE else { throw StorageHold.corrupt }
            return value
        }
    }
    private func scalarText(_ sql: String) throws -> String {
        try withStatement(sql) { statement in
            let code = sqlite3_step(statement)
            guard code == SQLITE_ROW else { throw code == SQLITE_DONE ? StorageHold.corrupt : sqliteHold(code) }
            guard let pointer = sqlite3_column_text(statement, 0) else { throw StorageHold.corrupt }
            let value = String(cString: pointer)
            guard sqlite3_step(statement) == SQLITE_DONE else { throw StorageHold.corrupt }
            return value
        }
    }
    private func oneBlob(_ sql: String, strings: [String]) throws -> Data? {
        try withStatement(sql, strings: strings) { statement in
            let result = sqlite3_step(statement)
            if result == SQLITE_DONE { return nil }
            guard result == SQLITE_ROW else { throw sqliteHold(result) }
            let bytes = try columnBlob(statement, 0)
            guard sqlite3_step(statement) == SQLITE_DONE else { throw StorageHold.corrupt }
            return bytes
        }
    }
}
