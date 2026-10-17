// SPDX-License-Identifier: MIT
import XCTest
import Foundation
import WebKit
import Capacitor
import GSIPStorageCore
@testable import App

final class RecordingPrototypeSchemeTask: NSObject, WKURLSchemeTask {
    let request: URLRequest
    var responseCount = 0
    var receivedBytes = 0
    var finishedCount = 0
    var failedCount = 0
    init(_ request: URLRequest) { self.request = request }
    func didReceive(_ response: URLResponse) { responseCount += 1 }
    func didReceive(_ data: Data) { receivedBytes += data.count }
    func didFinish() { finishedCount += 1 }
    func didFailWithError(_ error: Error) { failedCount += 1 }
}

@MainActor
final class AssetRequestGateTests: XCTestCase {
    private func request(_ path: String) -> URLRequest { URLRequest(url: URL(string: "capacitor://localhost" + path)!) }

    func testExactBundledAssetsOnlyAndClosedActivation() throws {
        let gate = AssetRequestGate(isCurrent: { true })
        XCTAssertTrue((gate.decision(for: request("/index.html"))) == (.bundled("index.html")))
        XCTAssertTrue((gate.decision(for: request("/gsip-activation.json"))) == (.bundled("gsip-activation.json")))
        let activation = try JSONSerialization.jsonObject(with: gate.bundledBytes("gsip-activation.json")) as? [String: Bool]
        XCTAssertTrue(activation == ["capture_live": false, "library_intake_live": false])
        XCTAssertThrowsError(try gate.bundledBytes("../synthetic"))
        XCTAssertThrowsError(try gate.bundledBytes("capacitor.js"))
    }

    func testSpecialFilesProxyTraversalAliasesAndRemoteOriginsAreDenied() {
        let gate = AssetRequestGate(isCurrent: { true })
        for path in ["/", "/_capacitor_file_/synthetic", "/_capacitor_http_interceptor_?u=https://synthetic.test", "/_capacitor_https_interceptor_", "/../index.html", "/%2e%2e/index.html", "/%69ndex.html", "//index.html", "/index.html?synthetic", "/index.html#synthetic", "/cordova.js", "/unknown"] {
            XCTAssertTrue((gate.decision(for: request(path))) == (.denied))
        }
        for url in ["https://localhost/index.html", "capacitor://localhost.synthetic.test/index.html", "capacitor://localhost:1/index.html", "file:///synthetic/index.html", "capacitor://synthetic@localhost/index.html"] {
            XCTAssertTrue((gate.decision(for: URLRequest(url: URL(string: url)!))) == (.denied))
        }
        var post = request("/index.html"); post.httpMethod = "POST"
        XCTAssertTrue((gate.decision(for: post)) == (.denied))
        for header in ["Range", "Cookie", "Authorization"] {
            var value = request("/index.html"); value.setValue("synthetic", forHTTPHeaderField: header)
            XCTAssertTrue((gate.decision(for: value)) == (.denied))
        }
    }

    func testActualSchemeTaskDenyHasNoResponseOrBytes() {
        let gate = AssetRequestGate(isCurrent: { true })
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        let webView = WKWebView(frame: .zero, configuration: configuration)
        let denied = RecordingPrototypeSchemeTask(request("/_capacitor_file_/synthetic"))
        gate.webView(webView, start: denied)
        XCTAssertTrue(denied.failedCount == 1 && denied.responseCount == 0 && denied.receivedBytes == 0 && denied.finishedCount == 0)
        let allowed = RecordingPrototypeSchemeTask(request("/gsip-activation.json"))
        gate.webView(webView, start: allowed)
        XCTAssertTrue(allowed.failedCount == 0 && allowed.responseCount == 1 && allowed.receivedBytes > 0 && allowed.finishedCount == 1)
    }

    func testOpaqueCanaryExpiresAndSymlinkOrRootPolicyCannotBypass() throws {
        let fixture = try HostOwnedCanaryFixture()
        let broker = try fixture.broker()
        let handle = try broker.issueSyntheticCanary()
        let gate = AssetRequestGate(isCurrent: { fixture.active }, broker: broker)
        XCTAssertTrue(gate.decision(for: request("/gsip-canary/" + handle)) == .canary(handle))
        XCTAssertTrue((gate.decision(for: request("/gsip-canary/" + String(repeating: "0", count: 64)))) == (.denied))
        XCTAssertTrue((gate.decision(for: request("/gsip-canary/" + handle + "/index.html"))) == (.denied))
        fixture.active = false
        XCTAssertTrue((gate.decision(for: request("/gsip-canary/" + handle))) == (.denied))
        XCTAssertTrue((gate.decision(for: request("/index.html"))) == (.denied))
    }
}
