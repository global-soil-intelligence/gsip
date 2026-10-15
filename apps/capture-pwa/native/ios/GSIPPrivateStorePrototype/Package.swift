// swift-tools-version: 5.9
// SPDX-License-Identifier: MIT
import PackageDescription

let package = Package(
    name: "GSIPPrivateStorePrototype",
    platforms: [.iOS(.v15)],
    products: [.library(name: "GSIPStorageCore", targets: ["GSIPStorageCore"])],
    targets: [
        .target(name: "GSIPStorageCore", sources: [
            "StorageContract.swift", "ExcludedSQLiteStore.swift", "KeychainAnchor.swift", "StorageCoordinator.swift"
        ]),
        .testTarget(name: "GSIPStorageCoreTests", dependencies: ["GSIPStorageCore"], sources: [
            "ExcludedSQLiteStoreTests.swift", "KeychainAnchorTests.swift", "StorageCoordinatorTests.swift", "NativeTestDoubles.swift"
        ])
    ]
)
