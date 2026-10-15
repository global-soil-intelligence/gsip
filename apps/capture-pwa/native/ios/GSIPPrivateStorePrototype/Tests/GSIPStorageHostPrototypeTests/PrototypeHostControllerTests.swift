// SPDX-License-Identifier: MIT
import XCTest
import Foundation
import UIKit
import WebKit
import Capacitor
import Cordova
import GSIPStorageCore
@testable import App

@MainActor
final class PrototypeHostControllerTests: XCTestCase {
    private func javascript(_ view: WKWebView, _ source: String) async throws -> Any? {
        try await withCheckedThrowingContinuation { continuation in
            view.evaluateJavaScript(source) { result, error in
                if let error { continuation.resume(throwing: error) }
                else { continuation.resume(returning: result) }
            }
        }
    }
    private func eventually(_ predicate: () -> Bool) async throws {
        for _ in 0..<500 {
            if predicate() { return }
            try await Task.sleep(nanoseconds: 20_000_000)
        }
        throw StorageHold.unavailable
    }
    private func load(_ controller: PrototypeHostController) async throws -> WKWebView {
        let view = try XCTUnwrap(controller.webView)
        try await eventually { view.url?.absoluteString == "capacitor://localhost/index.html" && !view.isLoading }
        _ = try await javascript(view, "window.__syntheticOutcomes = []; window.Capacitor.fromNative = function(value) { window.__syntheticOutcomes.push(value); }; true")
        return view
    }
    private func message(_ method: String, callback: String, options: [String: Any]) throws -> String {
        let value: [String: Any] = ["type": "message", "pluginId": "GSIPStoragePrototype", "methodName": method, "callbackId": callback, "options": options]
        let encoded = try JSONSerialization.data(withJSONObject: value)
        guard let result = String(data: encoded, encoding: .utf8) else { throw StorageHold.invalidRequest }
        return "window.webkit.messageHandlers.bridge.postMessage(" + result + ");"
    }

    func testAllConstructedControllersStartHeldWithoutWebKitOrBridge() {
        let controller = PrototypeHostController()
        controller.loadViewIfNeeded()
        XCTAssertTrue((controller.state) == (.held))
        XCTAssertTrue((controller.webView) == nil)
        XCTAssertTrue((controller.capacitorBridge) == nil)
        XCTAssertTrue((controller.messageGate) == nil)
        XCTAssertFalse(controller.view is WKWebView)
    }

    func testStoryboardStartupIsSameHeldController() throws {
        let storyboard = UIStoryboard(name: "Main", bundle: .main)
        let controller = try XCTUnwrap(storyboard.instantiateInitialViewController() as? PrototypeHostController)
        controller.loadViewIfNeeded()
        XCTAssertTrue((controller.state) == (.held))
        XCTAssertTrue((controller.webView) == nil)
        XCTAssertTrue((controller.capacitorBridge) == nil)
    }

    func testUnadmittedOrSuspendedLeaseNeverConstructsWebView() {
        let fixture = HostSyntheticFixture()
        let controller = PrototypeHostController()
        XCTAssertFalse(controller.startSyntheticProbe(coordinator: fixture.coordinator, lease: fixture.lease))
        XCTAssertTrue((controller.webView) == nil)
        XCTAssertTrue(fixture.admit() == .admitted(fixture.lease))
        fixture.coordinator.suspend()
        XCTAssertFalse(controller.startSyntheticProbe(coordinator: fixture.coordinator, lease: fixture.lease))
        XCTAssertTrue((controller.webView) == nil)
    }

    func testInjectedAdmissionConstructsNonpersistentGatedHostThenLifecycleRevokes() throws {
        let fixture = HostSyntheticFixture()
        XCTAssertTrue(fixture.admit() == .admitted(fixture.lease))
        let controller = PrototypeHostController()
        XCTAssertTrue(controller.startSyntheticProbe(coordinator: fixture.coordinator, lease: fixture.lease))
        let webView = try XCTUnwrap(controller.webView)
        let bridge = try XCTUnwrap(controller.capacitorBridge)
        XCTAssertFalse(webView.configuration.websiteDataStore.isPersistent)
        XCTAssertFalse(bridge.autoRegisterPlugins)
        XCTAssertFalse(bridge.config.handleApplicationNotifications)
        XCTAssertFalse(bridge.config.loggingEnabled)
        XCTAssertTrue(webView.navigationDelegate === controller.delegationHandler)
        XCTAssertTrue(webView.uiDelegate === controller.delegationHandler)
        XCTAssertTrue(controller.messageGate?.expectedWebView === webView)
        XCTAssertTrue((bridge.plugin(withName: "GSIPStoragePrototype")) != nil)
        for name in ["Camera", "Filesystem", "LocalNotifications"] { XCTAssertTrue((bridge.plugin(withName: name)) == nil) }
        XCTAssertTrue((HTTPCookieStorage.shared.cookieAcceptPolicy) == (.never))
        controller.suspendForLifecycle()
        XCTAssertTrue((controller.state) == (.suspended))
        XCTAssertFalse(fixture.coordinator.isCurrent(fixture.lease))
        XCTAssertTrue(webView.isHidden)
        XCTAssertFalse(controller.startSyntheticProbe(coordinator: fixture.coordinator, lease: fixture.lease))
    }

    func testActualRawBridgeSerializesPutThenClearThroughNativeReplyDrain() async throws {
        let fixture = HostSyntheticFixture()
        XCTAssertTrue(fixture.admit() == .admitted(fixture.lease))
        let controller = PrototypeHostController()
        XCTAssertTrue(controller.startSyntheticProbe(coordinator: fixture.coordinator, lease: fixture.lease))
        let view = try await load(controller)
        let put = try message("put", callback: "synthetic-first", options: ["store": "submissions", "operationID": "synthetic-first", "expectedRevision": 0, "canary": "alpha"])
        let earlyClear = try message("clear", callback: "synthetic-busy", options: ["operationID": "synthetic-busy"])
        _ = try await javascript(view, put + earlyClear + "true")
        try await eventually { controller.completedReplyCount == 1 }
        XCTAssertTrue(controller.messageGate?.acceptedCount == 1 && controller.messageGate?.rejectedCount == 1)
        XCTAssertTrue(fixture.database.value.generation == 0)
        let first = try await javascript(view, "window.__syntheticOutcomes.length === 1 && window.__syntheticOutcomes[0].success === true && window.__syntheticOutcomes[0].data.generation === 0")
        XCTAssertTrue(first as? Bool == true)
        _ = try await javascript(view, try message("clear", callback: "synthetic-after-drain", options: ["operationID": "synthetic-after-drain"]) + "true")
        try await eventually { controller.completedReplyCount == 2 }
        XCTAssertTrue(fixture.database.value.generation == 1)
        let ordered = try await javascript(view, "window.__syntheticOutcomes.length === 2 && window.__syntheticOutcomes[0].data.generation === 0 && window.__syntheticOutcomes[1].data.generation === 1")
        XCTAssertTrue(ordered as? Bool == true)
        controller.suspendForLifecycle()
    }

    func testActualRawBridgeLifecycleRaceEmitsNoStaleSuccess() async throws {
        let fixture = HostSyntheticFixture()
        XCTAssertTrue(fixture.admit() == .admitted(fixture.lease))
        let controller = PrototypeHostController()
        XCTAssertTrue(controller.startSyntheticProbe(coordinator: fixture.coordinator, lease: fixture.lease))
        let view = try await load(controller)
        fixture.database.afterCommitValidation = { [weak controller] in
            DispatchQueue.main.async { controller?.suspendForLifecycle() }
        }
        _ = try await javascript(view, try message("put", callback: "synthetic-lifecycle-race", options: ["store": "draftPhotos", "operationID": "synthetic-lifecycle-race", "expectedRevision": 0, "canary": "beta"]) + "true")
        try await eventually { controller.state == .suspended }
        XCTAssertTrue((controller.bridgedWebView) == nil)
        let empty = try await javascript(view, "window.__syntheticOutcomes.length === 0")
        XCTAssertTrue(empty as? Bool == true)
        XCTAssertTrue(controller.completedReplyCount == 0)
    }

    func testProtectedDataOrSceneNotificationHoldsWithoutAutomaticReopen() {
        let fixture = HostSyntheticFixture()
        XCTAssertTrue(fixture.admit() == .admitted(fixture.lease))
        let controller = PrototypeHostController()
        XCTAssertTrue(controller.startSyntheticProbe(coordinator: fixture.coordinator, lease: fixture.lease))
        NotificationCenter.default.post(name: UIApplication.protectedDataWillBecomeUnavailableNotification, object: nil)
        XCTAssertTrue((controller.state) == (.suspended))
        XCTAssertFalse(fixture.coordinator.isCurrent(fixture.lease))
        NotificationCenter.default.post(name: UIApplication.protectedDataDidBecomeAvailableNotification, object: nil)
        XCTAssertTrue((controller.state) == (.suspended))
    }
}
