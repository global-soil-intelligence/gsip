// SPDX-License-Identifier: MIT
import XCTest
import Foundation
import WebKit
import Capacitor
import GSIPStorageCore
@testable import App

/// An inert test-owned scheme page. No ordinary PWA, native bridge, persistence or network.
@MainActor
final class HostWebProbe: NSObject, WKURLSchemeHandler {
    private(set) var webView: WKWebView!
    private let html = Data("<!doctype html><meta charset=utf-8><title>Synthetic probe</title>".utf8)
    init(gate: BridgeMessageGate? = nil, delegation: PrototypeDelegationHandler? = nil) {
        super.init()
        HTTPCookieStorage.shared.cookieAcceptPolicy = .never
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        configuration.setURLSchemeHandler(self, forURLScheme: "capacitor")
        if let gate { configuration.userContentController.add(gate, name: "bridge") }
        webView = WKWebView(frame: .zero, configuration: configuration)
        gate?.expectedWebView = webView
        webView.navigationDelegate = delegation
        webView.uiDelegate = delegation
    }
    func webView(_ webView: WKWebView, start urlSchemeTask: WKURLSchemeTask) {
        guard let url = urlSchemeTask.request.url,
              url.absoluteString == "capacitor://localhost/index.html" else {
            urlSchemeTask.didFailWithError(StorageHold.boundary)
            return
        }
        urlSchemeTask.didReceive(URLResponse(url: url, mimeType: "text/html", expectedContentLength: html.count, textEncodingName: "utf-8"))
        urlSchemeTask.didReceive(html)
        urlSchemeTask.didFinish()
    }
    func webView(_ webView: WKWebView, stop urlSchemeTask: WKURLSchemeTask) { }
    func javascript(_ source: String) async throws -> Any? {
        try await withCheckedThrowingContinuation { continuation in
            webView.evaluateJavaScript(source) { result, error in
                if let error { continuation.resume(throwing: error) }
                else { continuation.resume(returning: result) }
            }
        }
    }
    func load() async throws {
        webView.load(URLRequest(url: URL(string: "capacitor://localhost/index.html")!))
        for _ in 0..<500 {
            if webView.url?.absoluteString == "capacitor://localhost/index.html", !webView.isLoading,
               (try? await javascript("document.readyState")) as? String == "complete" { return }
            try await Task.sleep(nanoseconds: 20_000_000)
        }
        throw StorageHold.unavailable
    }
    func waitForMessages(_ gate: BridgeMessageGate, total: Int) async throws {
        for _ in 0..<500 {
            if gate.acceptedCount + gate.rejectedCount >= total { return }
            try await Task.sleep(nanoseconds: 20_000_000)
        }
        throw StorageHold.unavailable
    }
}

@MainActor
final class BridgeMessageGateTests: XCTestCase {
    private func body(plugin: String = BridgeMessageGate.pluginID, method: String = "status",
                      options: [String: Any] = [:]) -> [String: Any] {
        ["type": "message", "pluginId": plugin, "methodName": method,
         "callbackId": "synthetic-callback", "options": options]
    }
    private func permits(_ gate: BridgeMessageGate, _ value: Any, main: Bool = true,
                         scheme: String = "capacitor", host: String = "localhost", port: Int = 0,
                         owned: Bool = true) -> Bool {
        gate.permits(body: value, name: "bridge", isMainFrame: main, scheme: scheme,
                     host: host, port: port, isOwnedWebView: owned)
    }

    func testExactEnvelopeFrameOriginAndLeaseAreAllRequired() {
        var active = true
        let gate = BridgeMessageGate(isCurrent: { active }, forward: { _, _ in })
        XCTAssertTrue(permits(gate, body()))
        XCTAssertFalse(permits(gate, body(), main: false))
        XCTAssertFalse(permits(gate, body(), scheme: "https"))
        XCTAssertFalse(permits(gate, body(), host: "localhost.synthetic.test"))
        XCTAssertFalse(permits(gate, body(), port: 1))
        XCTAssertFalse(permits(gate, body(), owned: false))
        XCTAssertFalse(permits(gate, body().merging(["owner": "synthetic"]){ _, new in new }))
        XCTAssertFalse(permits(gate, ["type": "js.error", "error": ["message": "synthetic"]]))
        XCTAssertFalse(permits(gate, ["type": "cordova", "service": "synthetic", "action": "synthetic"]))
        XCTAssertFalse(permits(gate, body(method: "put", options: ["store": "submissions", "operationID": "synthetic", "expectedRevision": 0, "canary": String(repeating: "x", count: StorageLimits.frameBytes)])))
        active = false
        XCTAssertFalse(permits(gate, body()))
        active = true
        gate.revoke()
        XCTAssertFalse(permits(gate, body()))
    }

    func testEveryCoreAndClassAliasIsDeniedBeforeUpstreamLookup() {
        let gate = BridgeMessageGate(isCurrent: { true }, forward: { _, _ in XCTFail("A rejected request reached upstream.") })
        for plugin in ["Console", "CapacitorHttp", "CAPHttpPlugin", "CapacitorCookies", "CAPCookiesPlugin", "WebView", "CAPWebViewPlugin", "SystemBars", "Camera", "LocalNotifications", "PrototypeStorePlugin", "App.PrototypeStorePlugin", "Cordova"] {
            XCTAssertFalse(permits(gate, body(plugin: plugin)))
        }
    }

    func testActualWebKitMessagesRejectRawAliasesCordovaAndSubframes() async throws {
        var forwarded = 0
        let gate = BridgeMessageGate(isCurrent: { true }, forward: { _, _ in forwarded += 1 })
        let probe = HostWebProbe(gate: gate)
        try await probe.load()
        var messages: [[String: Any]] = [body()]
        for plugin in ["CapacitorHttp", "CAPCookiesPlugin", "CAPWebViewPlugin", "PrototypeStorePlugin"] { messages.append(body(plugin: plugin)) }
        messages.append(["type": "js.error", "error": ["message": "synthetic"]])
        messages.append(["type": "cordova", "service": "synthetic", "action": "synthetic"])
        let encoded = String(data: try JSONSerialization.data(withJSONObject: messages), encoding: .utf8)!
        _ = try await probe.javascript("for (const value of " + encoded + ") { window.webkit.messageHandlers.bridge.postMessage(value); }; true")
        let childBody = String(data: try JSONSerialization.data(withJSONObject: body()), encoding: .utf8)!
        let childHTML = "<script>window.webkit.messageHandlers.bridge.postMessage(" + childBody + ");</script>"
        let childLiteral = String(data: try JSONSerialization.data(withJSONObject: [childHTML]), encoding: .utf8)!
        _ = try await probe.javascript("var child = document.createElement('iframe'); child.srcdoc = " + childLiteral + "[0]; document.body.appendChild(child); true")
        try await probe.waitForMessages(gate, total: messages.count + 1)
        XCTAssertTrue(forwarded == 1 && gate.acceptedCount == 1 && gate.rejectedCount == messages.count)
    }

    func testActualWebKitStaleAndRemovedHandlerFailClosed() async throws {
        var active = true
        var forwarded = 0
        let gate = BridgeMessageGate(isCurrent: { active }, forward: { _, _ in forwarded += 1 })
        let probe = HostWebProbe(gate: gate)
        try await probe.load()
        active = false
        let encoded = String(data: try JSONSerialization.data(withJSONObject: body()), encoding: .utf8)!
        _ = try await probe.javascript("window.webkit.messageHandlers.bridge.postMessage(" + encoded + "); true")
        try await probe.waitForMessages(gate, total: 1)
        XCTAssertTrue(forwarded == 0 && gate.rejectedCount == 1)
        // Upstream cleanup removes this name. No route is installed as a fallback.
        probe.webView.configuration.userContentController.removeScriptMessageHandler(forName: "bridge")
        let missing = try await probe.javascript("typeof window.webkit?.messageHandlers?.bridge === 'undefined'")
        XCTAssertTrue(missing as? Bool == true)
        XCTAssertTrue(forwarded == 0)
    }
}
