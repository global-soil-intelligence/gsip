// SPDX-License-Identifier: MIT
import Foundation
import UIKit
import WebKit
import Capacitor
import GSIPStorageCore

/// Avoid upstream plugin overrides, external URL opening, cookie prompts and auto-reload.
final class PrototypeDelegationHandler: WebViewDelegationHandler {
    private let isCurrent: () -> Bool
    private let hold: () -> Void
    private(set) var finishedCount = 0
    private var initialNavigationClaimed = false
    private var navigationStarted = false

    init(isCurrent: @escaping () -> Bool, hold: @escaping () -> Void) {
        self.isCurrent = isCurrent
        self.hold = hold
        super.init()
    }

    func permitsNavigation(_ url: URL?, mainFrame: Bool, newWindow: Bool) -> Bool {
        guard isCurrent(), mainFrame, !newWindow, let url,
              let parts = URLComponents(url: url, resolvingAgainstBaseURL: false),
              parts.scheme == "capacitor", parts.host == "localhost", parts.port == nil,
              parts.user == nil, parts.password == nil, parts.query == nil, parts.fragment == nil,
              parts.percentEncodedPath == "/index.html" else { return false }
        return true
    }

    override func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction,
                          decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard !initialNavigationClaimed,
              permitsNavigation(navigationAction.request.url,
                                mainFrame: navigationAction.targetFrame?.isMainFrame == true,
                                newWindow: navigationAction.targetFrame == nil) else {
            hold()
            decisionHandler(.cancel)
            return
        }
        initialNavigationClaimed = true
        decisionHandler(.allow)
    }

    override func webView(_ webView: WKWebView, didStartProvisionalNavigation navigation: WKNavigation!) {
        guard isCurrent(), !navigationStarted else { webView.stopLoading(); hold(); return }
        navigationStarted = true
    }

    override func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        if isCurrent() { finishedCount += 1 } else { hold() }
    }

    override func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) { hold() }
    override func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) { hold() }
    override func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
        webView.stopLoading()
        hold()
    }

    override func webView(_ webView: WKWebView, requestMediaCapturePermissionFor origin: WKSecurityOrigin,
                          initiatedByFrame frame: WKFrameInfo, type: WKMediaCaptureType,
                          decisionHandler: @escaping (WKPermissionDecision) -> Void) { decisionHandler(.deny) }

    override func webView(_ webView: WKWebView, requestDeviceOrientationAndMotionPermissionFor origin: WKSecurityOrigin,
                          initiatedByFrame frame: WKFrameInfo,
                          decisionHandler: @escaping (WKPermissionDecision) -> Void) { decisionHandler(.deny) }

    override func webView(_ webView: WKWebView, runJavaScriptAlertPanelWithMessage message: String,
                          initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping () -> Void) { completionHandler() }

    override func webView(_ webView: WKWebView, runJavaScriptConfirmPanelWithMessage message: String,
                          initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) { completionHandler(false) }

    override func webView(_ webView: WKWebView, runJavaScriptTextInputPanelWithPrompt prompt: String,
                          defaultText: String?, initiatedByFrame frame: WKFrameInfo,
                          completionHandler: @escaping (String?) -> Void) { completionHandler(nil) }

    override func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration,
                          for navigationAction: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? { nil }
}
