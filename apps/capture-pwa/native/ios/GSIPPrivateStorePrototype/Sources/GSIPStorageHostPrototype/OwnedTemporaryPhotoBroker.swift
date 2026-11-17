// SPDX-License-Identifier: MIT
import Foundation
import Darwin
import CryptoKit
import GSIPStorageCore

/// A native-created synthetic file only. There is no caller path/URI or camera registration API.
final class OwnedTemporaryPhotoBroker {
    private static let filename = "gsip-photo-canary.bin"
    private static let canary = Data("GSIP native synthetic photo canary".utf8)
    private let root: URL
    private let rootFD: Int32
    private let rootDevice: dev_t
    private let rootInode: ino_t
    private let lease: StorageLease
    private let isCurrent: () -> Bool
    private let protectedDataAvailable: () -> Bool
    private let now: () -> TimeInterval
    private let created: TimeInterval
    private let expires: TimeInterval
    private let handle: String
    private var fileIdentity: (dev_t, ino_t)?
    private var revoked = false

    init(identity: SyntheticRunIdentity, lease: StorageLease, isCurrent: @escaping () -> Bool,
         now: @escaping () -> TimeInterval = { ProcessInfo.processInfo.systemUptime },
         protectedDataAvailable: @escaping () -> Bool = { false }) throws {
        #if targetEnvironment(simulator)
        guard Bundle.main.bundleIdentifier == "com.globalsoilintelligence.app.storageprototype",
              ProcessInfo.processInfo.environment["SIMULATOR_UDID"]?.isEmpty == false,
              lease.isValid, isCurrent(), protectedDataAvailable(), StorageLimits.validIdentifier(identity.nonce),
              let libraryURL = FileManager.default.urls(for: .libraryDirectory, in: .userDomainMask).first else { throw StorageHold.boundary }
        let library = libraryURL.resolvingSymlinksInPath().standardizedFileURL
        let libraryFD = open(library.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW)
        guard libraryFD >= 0 else { throw StorageHold.boundary }
        defer { close(libraryFD) }
        let parentFD = openat(libraryFD, "GSIPStoragePrototype-v1", O_RDONLY | O_DIRECTORY | O_NOFOLLOW)
        guard parentFD >= 0 else { throw StorageHold.boundary }
        defer { close(parentFD) }
        let descriptor = openat(parentFD, identity.nonce, O_RDONLY | O_DIRECTORY | O_NOFOLLOW)
        guard descriptor >= 0 else { throw StorageHold.boundary }
        var identityStat = stat()
        guard fstat(descriptor, &identityStat) == 0, (identityStat.st_mode & S_IFMT) == S_IFDIR,
              identityStat.st_uid == geteuid(), identityStat.st_mode & 0o777 == 0o700 else {
            close(descriptor); throw StorageHold.boundary
        }
        root = library.appendingPathComponent("GSIPStoragePrototype-v1", isDirectory: true)
            .appendingPathComponent(identity.nonce, isDirectory: true)
        rootFD = descriptor
        rootDevice = identityStat.st_dev
        rootInode = identityStat.st_ino
        self.lease = lease
        self.isCurrent = isCurrent
        self.protectedDataAvailable = protectedDataAvailable
        self.now = now
        created = now()
        expires = created + 60
        handle = SHA256.hash(data: Data((identity.nonce + ":" + lease.owner + ":" + lease.launch + ":" + String(lease.generation)).utf8))
            .map { String(format: "%02x", $0) }.joined()
        do { try validateRoot() } catch { close(descriptor); throw StorageHold.boundary }
        #else
        throw StorageHold.unsupportedPlatform
        #endif
    }

    deinit { close(rootFD) }

    private func validateRoot() throws {
        guard !revoked, isCurrent(), protectedDataAvailable(), now() >= created, now() < expires else { throw StorageHold.staleLease }
        var descriptorStat = stat()
        var pathStat = stat()
        guard fstat(rootFD, &descriptorStat) == 0,
              lstat(root.path, &pathStat) == 0,
              descriptorStat.st_dev == rootDevice, descriptorStat.st_ino == rootInode,
              pathStat.st_dev == rootDevice, pathStat.st_ino == rootInode,
              (pathStat.st_mode & S_IFMT) == S_IFDIR,
              pathStat.st_uid == geteuid(), pathStat.st_mode & 0o777 == 0o700,
              descriptorStat.st_uid == geteuid(), descriptorStat.st_mode & 0o777 == 0o700,
              root.resolvingSymlinksInPath() == root.standardizedFileURL else { throw StorageHold.boundary }
        var fresh = URL(fileURLWithPath: root.path)
        fresh.removeAllCachedResourceValues()
        let values = try fresh.resourceValues(forKeys: [.fileProtectionKey, .isExcludedFromBackupKey, .isSymbolicLinkKey, .isDirectoryKey])
        guard values.isExcludedFromBackup == true, values.isSymbolicLink == false,
              values.isDirectory == true, values.fileProtection == .complete else { throw StorageHold.boundary }
    }

    private func validateFile(_ descriptor: Int32) throws -> stat {
        try validateRoot()
        var descriptorStat = stat()
        var pathStat = stat()
        guard fstat(descriptor, &descriptorStat) == 0,
              fstatat(rootFD, Self.filename, &pathStat, AT_SYMLINK_NOFOLLOW) == 0,
              descriptorStat.st_dev == pathStat.st_dev, descriptorStat.st_ino == pathStat.st_ino,
              (pathStat.st_mode & S_IFMT) == S_IFREG, pathStat.st_nlink == 1,
              pathStat.st_uid == geteuid(), pathStat.st_mode & 0o777 == 0o600,
              descriptorStat.st_uid == geteuid(), descriptorStat.st_mode & 0o777 == 0o600 else { throw StorageHold.boundary }
        if let fileIdentity {
            guard fileIdentity.0 == pathStat.st_dev, fileIdentity.1 == pathStat.st_ino else { throw StorageHold.boundary }
        }
        let url = root.appendingPathComponent(Self.filename, isDirectory: false)
        var fresh = URL(fileURLWithPath: url.path)
        fresh.removeAllCachedResourceValues()
        let values = try fresh.resourceValues(forKeys: [.fileProtectionKey, .isExcludedFromBackupKey, .isSymbolicLinkKey])
        guard values.isExcludedFromBackup == true, values.isSymbolicLink == false,
              values.fileProtection == .complete else { throw StorageHold.boundary }
        return descriptorStat
    }

    func issueSyntheticCanary() throws -> String {
        try validateRoot()
        if fileIdentity != nil { _ = try read(handle: handle); return handle }
        let descriptor = openat(rootFD, Self.filename, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, mode_t(0o600))
        guard descriptor >= 0 else { throw StorageHold.boundary }
        defer { close(descriptor) }
        var url = root.appendingPathComponent(Self.filename, isDirectory: false)
        try (url as NSURL).setResourceValue(URLFileProtection.complete.rawValue, forKey: .fileProtectionKey)
        var metadata = URLResourceValues()
        metadata.isExcludedFromBackup = true
        try url.setResourceValues(metadata)
        let initial = try validateFile(descriptor)
        guard initial.st_size == 0 else { throw StorageHold.boundary }
        fileIdentity = (initial.st_dev, initial.st_ino)
        let written = Self.canary.withUnsafeBytes { bytes -> Int in
            guard let address = bytes.baseAddress else { return -1 }
            var offset = 0
            var interruptions = 0
            while offset < bytes.count {
                let result = write(descriptor, address.advanced(by: offset), bytes.count - offset)
                if result > 0 { offset += result }
                else if result < 0 && errno == EINTR && interruptions < 8 { interruptions += 1 }
                else { return -1 }
            }
            return offset
        }
        guard written == Self.canary.count, fsync(descriptor) == 0,
              try validateFile(descriptor).st_size == Self.canary.count else { throw StorageHold.boundary }
        return handle
    }

    func contains(handle candidate: String) -> Bool { (try? read(handle: candidate)) != nil }

    func read(handle candidate: String) throws -> Data {
        guard candidate == handle, fileIdentity != nil else { throw StorageHold.boundary }
        try validateRoot()
        let descriptor = openat(rootFD, Self.filename, O_RDONLY | O_NOFOLLOW)
        guard descriptor >= 0 else { throw StorageHold.boundary }
        defer { close(descriptor) }
        let before = try validateFile(descriptor)
        guard before.st_size == Self.canary.count else { throw StorageHold.boundary }
        var bytes = Data(count: Self.canary.count)
        let count = bytes.withUnsafeMutableBytes { buffer -> Int in
            guard let address = buffer.baseAddress else { return -1 }
            return pread(descriptor, address, buffer.count, 0)
        }
        let after = try validateFile(descriptor)
        guard count == Self.canary.count, before.st_size == after.st_size,
              SHA256.hash(data: bytes) == SHA256.hash(data: Self.canary) else { throw StorageHold.boundary }
        return bytes
    }

    /// Revocation preserves the owned bytes; only the disposable runner cleans its namespace.
    func revoke() { revoked = true }
}
