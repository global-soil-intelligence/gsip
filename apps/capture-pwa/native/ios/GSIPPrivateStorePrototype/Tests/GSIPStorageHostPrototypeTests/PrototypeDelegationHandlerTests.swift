// SPDX-License-Identifier: MIT
import XCTest
import Foundation
import UIKit
import WebKit
import Capacitor
import GSIPStorageCore
@testable import App

@MainActor
final class PrototypeDelegationHandlerTests: XCTestCase {
    func testOnlyExactOwnedMainNavigationCanProceed() {
        var active = true
        let handler = PrototypeDelegationHandler(isCurrent: { active }, hold: { })
        XCTAssertTrue(handler.permitsNavigation(URL(string: "capacitor://localhost/index.html"), mainFrame: true, newWindow: false))
        for value in ["https://synthetic.test/index.html", "file:///synthetic", "capacitor://localhost.synthetic.test/index.html", "capacitor://localhost:1/index.html", "capacitor://localhost/_capacitor_file_/synthetic", "capacitor://localhost/_capacitor_http_interceptor_?u=https://synthetic.test", "capacitor://localhost/index.html?synthetic", "capacitor://localhost/index.html#synthetic", "capacitor://synthetic@localhost/index.html"] {
            XCTAssertFalse(handler.permitsNavigation(URL(string: value), mainFrame: true, newWindow: false))
        }
        XCTAssertFalse(handler.permitsNavigation(URL(string: "capacitor://localhost/index.html"), mainFrame: false, newWindow: false))
        XCTAssertFalse(handler.permitsNavigation(URL(string: "capacitor://localhost/index.html"), mainFrame: true, newWindow: true))
        active = false
        XCTAssertFalse(handler.permitsNavigation(URL(string: "capacitor://localhost/index.html"), mainFrame: true, newWindow: false))
    }

    func testActualWebKitCookieAndOrdinaryPromptsCompleteWithoutEchoOrCoreCalls() async throws {
        let handler = PrototypeDelegationHandler(isCurrent: { true }, hold: { })
        let probe = HostWebProbe(delegation: handler)
        try await probe.load()
        for kind in ["CapacitorCookies.get", "CapacitorCookies.set", "CapacitorCookies.isEnabled", "CapacitorHttp", "synthetic"] {
            let prompt = String(data: try JSONSerialization.data(withJSONObject: ["type": kind, "action": "synthetic", "domain": "synthetic.test"]), encoding: .utf8)!
            let literal = String(data: try JSONSerialization.data(withJSONObject: [prompt]), encoding: .utf8)!
            let denied = try await probe.javascript("prompt(" + literal + "[0], 'synthetic') === null")
            XCTAssertTrue(denied as? Bool == true)
        }
        let confirmation = try await probe.javascript("confirm('synthetic') === false")
        let alert = try await probe.javascript("alert('synthetic'); true")
        let popup = try await probe.javascript("window.open('https://synthetic.test') === null")
        XCTAssertTrue(confirmation as? Bool == true)
        XCTAssertTrue(alert as? Bool == true)
        XCTAssertTrue(popup as? Bool == true)
        XCTAssertTrue(probe.webView.url?.absoluteString == "capacitor://localhost/index.html")
    }

    func testActualSameOriginReloadRevokesPendingNativeRepliesBeforeReplacementDocument() async throws {
        var active = true
        var holds = 0
        var forwarded = 0
        let gate = BridgeMessageGate(isCurrent: { active }, forward: { _, _ in forwarded += 1 })
        let handler = PrototypeDelegationHandler(isCurrent: { active }, hold: { active = false; holds += 1; gate.revoke() })
        let probe = HostWebProbe(gate: gate, delegation: handler)
        try await probe.load()
        let body: [String: Any] = ["type": "message", "pluginId": "GSIPStoragePrototype", "methodName": "status", "callbackId": "synthetic-delayed", "options": [:]]
        let encoded = String(data: try JSONSerialization.data(withJSONObject: body), encoding: .utf8)!
        _ = try await probe.javascript("window.webkit.messageHandlers.bridge.postMessage(" + encoded + "); true")
        try await probe.waitForMessages(gate, total: 1)
        XCTAssertTrue(forwarded == 1)
        _ = try? await probe.javascript("location.reload(); true")
        for _ in 0..<500 {
            if holds > 0 { break }
            try await Task.sleep(nanoseconds: 20_000_000)
        }
        XCTAssertTrue(holds > 0 && !active)
        XCTAssertFalse(gate.permits(body: body, name: "bridge", isMainFrame: true, scheme: "capacitor", host: "localhost", port: 0, isOwnedWebView: true))
        XCTAssertTrue(handler.finishedCount == 1)
    }

    func testProcessTerminationHoldsWithoutReloadOrReopen() async throws {
        var active = true
        var holds = 0
        let handler = PrototypeDelegationHandler(isCurrent: { active }, hold: { active = false; holds += 1 })
        let probe = HostWebProbe(delegation: handler)
        try await probe.load()
        handler.webViewWebContentProcessDidTerminate(probe.webView)
        XCTAssertTrue(holds == 1 && !active && !probe.webView.isLoading)
        XCTAssertFalse(handler.permitsNavigation(URL(string: "capacitor://localhost/index.html"), mainFrame: true, newWindow: false))
    }
}
