// SPDX-License-Identifier: MIT
import Foundation
import UIKit
import WebKit
import Capacitor
import Cordova
import GSIPStorageCore

/// Every initializer remains held. Only a native synthetic test may admit this host.
final class PrototypeHostController: UIViewController, CAPBridgeDelegate {
    enum State: Equatable { case held, constructing, admitted, suspended }
    static let bundleIdentifier = "com.globalsoilintelligence.app.storageprototype"
    private(set) var state: State = .held
    private(set) var webView: WKWebView?
    private(set) var capacitorBridge: CapacitorBridge?
    private(set) var messageGate: BridgeMessageGate?
    private(set) var delegationHandler: PrototypeDelegationHandler?
    private var session: PrototypeStorageSession?
    private(set) var completedReplyCount = 0
    private var observations: [NSObjectProtocol] = []

    var bridgedWebView: WKWebView? { session?.isCurrent == true ? webView : nil }
    var bridgedViewController: UIViewController? { self }

    override init(nibName nibNameOrNil: String?, bundle nibBundleOrNil: Bundle?) {
        super.init(nibName: nibNameOrNil, bundle: nibBundleOrNil)
    }
    convenience init() { self.init(nibName: nil, bundle: nil) }
    required init?(coder: NSCoder) { super.init(coder: coder) }

    override func loadView() {
        // No WKWebView, default data store, Keychain or database access on startup.
        let holding = UIView(frame: .zero)
        holding.backgroundColor = .systemBackground
        view = holding
    }

    @discardableResult
    func startSyntheticProbe(coordinator: StorageCoordinator, lease: StorageLease) -> Bool {
        #if targetEnvironment(simulator)
        guard state == .held, Bundle.main.bundleIdentifier == Self.bundleIdentifier,
              ProcessInfo.processInfo.environment["SIMULATOR_UDID"]?.isEmpty == false,
              UIApplication.shared.isProtectedDataAvailable, coordinator.isCurrent(lease),
              let assets = Bundle.main.resourceURL?.appendingPathComponent("public", isDirectory: true),
              let config = Bundle.main.url(forResource: "capacitor.config", withExtension: "json") else { return false }
        state = .constructing
        let binding = PrototypeStorageSession(coordinator: coordinator, lease: lease,
                                             hostIsActive: { true })
        session = binding
        let descriptor = InstanceDescriptor(at: assets, configuration: config, cordovaConfiguration: nil)
        descriptor.handleApplicationNotifications = false
        descriptor.loggingBehavior = .none
        descriptor.serverURL = nil
        descriptor.urlScheme = "capacitor"
        descriptor.urlHostname = "localhost"
        descriptor.allowedNavigationHostnames = []
        descriptor.pluginConfigurations = [:]
        descriptor.errorPath = nil
        let configuration = InstanceConfiguration(with: descriptor, isDebug: false)
        guard !configuration.handleApplicationNotifications, !configuration.loggingEnabled,
              configuration.localURL.absoluteString == "capacitor://localhost",
              configuration.serverURL == configuration.localURL else { suspendForLifecycle(); return false }
        CAPLog.enableLogging = false
        // This is the isolated test app's jar policy, never a jar read or deletion.
        HTTPCookieStorage.shared.cookieAcceptPolicy = .never
        guard HTTPCookieStorage.shared.cookieAcceptPolicy == .never else { suspendForLifecycle(); return false }
        let delegation = PrototypeDelegationHandler(isCurrent: { [weak binding] in binding?.isCurrent == true },
                                                  hold: { [weak self] in self?.suspendForLifecycle() })
        let gate = BridgeMessageGate(isCurrent: { [weak binding] in binding?.isCurrent == true },
                                     admit: { [weak binding] callback, request in binding?.register(callback: callback, request: request) == true },
                                     forward: { [weak delegation] controller, message in
                                         delegation?.userContentController(controller, didReceive: message)
                                     })
        delegation.contentController.removeScriptMessageHandler(forName: "bridge")
        delegation.contentController.add(gate, name: "bridge")
        let assetGate = AssetRequestGate(isCurrent: { [weak binding] in binding?.isCurrent == true })
        let webConfiguration = WKWebViewConfiguration()
        webConfiguration.websiteDataStore = WKWebsiteDataStore.nonPersistent()
        webConfiguration.userContentController = delegation.contentController
        webConfiguration.setURLSchemeHandler(assetGate, forURLScheme: "capacitor")
        webConfiguration.mediaTypesRequiringUserActionForPlayback = .all
        webConfiguration.allowsAirPlayForMediaPlayback = false
        guard !webConfiguration.websiteDataStore.isPersistent, binding.isCurrent else { suspendForLifecycle(); return false }
        let freshWebView = WKWebView(frame: .zero, configuration: webConfiguration)
        freshWebView.navigationDelegate = delegation
        freshWebView.uiDelegate = delegation
        freshWebView.allowsLinkPreview = false
        gate.expectedWebView = freshWebView
        webView = freshWebView
        messageGate = gate
        delegationHandler = delegation
        let bridge = CapacitorBridge(with: configuration, delegate: self,
                                     cordovaConfiguration: descriptor.cordovaConfiguration,
                                     assetHandler: assetGate, delegationHandler: delegation,
                                     autoRegisterPlugins: false)
        capacitorBridge = bridge
        let plugin = PrototypeStorePlugin()
        guard plugin.bind(binding, delivery: { [weak self, weak binding] call, result, lease, callback in
            DispatchQueue.main.async { [weak self, weak binding] in
                guard let self, let binding else { return }
                self.deliverReply(call, result: result, lease: lease, callback: callback, binding: binding)
            }
        }), !bridge.autoRegisterPlugins,
              !bridge.config.handleApplicationNotifications else { suspendForLifecycle(); return false }
        bridge.registerPluginInstance(plugin)
        guard binding.isCurrent else { suspendForLifecycle(); return false }
        for name in [UIApplication.protectedDataWillBecomeUnavailableNotification,
                     UIApplication.willResignActiveNotification, UIScene.didDisconnectNotification] {
            observations.append(NotificationCenter.default.addObserver(forName: name, object: nil, queue: .main) { [weak self] _ in
                self?.suspendForLifecycle()
            })
        }
        state = .admitted
        view = freshWebView
        // Handler/delegates/data store/notification policy were installed before this first request.
        guard binding.isCurrent else { suspendForLifecycle(); return false }
        freshWebView.load(URLRequest(url: URL(string: "capacitor://localhost/index.html")!))
        return true
        #else
        return false
        #endif
    }

    /// Upstream resolve queues another main block. Keep a single native call in flight
    /// through that block and a subsequent fixed WK drain, rather than reopening on a timer.
    private func deliverReply(_ call: CAPPluginCall, result: [String: Any]?, lease: StorageLease,
                              callback: String, binding: PrototypeStorageSession) {
        DispatchQueue.main.async { [weak self, weak binding] in
            guard let self, let binding else { return }
            guard self.state == .admitted, binding.isCurrent, binding.lease == lease,
                  let ownedView = self.bridgedWebView, ownedView === self.webView else {
                binding.complete(callback: callback)
                self.suspendForLifecycle()
                return
            }
            if let result { call.resolve(result) }
            else { call.reject("Synthetic storage is held.", "held") }
            // FIFO on this same main queue places this block after Capacitor's emission.
            DispatchQueue.main.async { [weak self, weak binding, weak ownedView] in
                guard let self, let binding, let ownedView,
                      binding.isCurrent, binding.lease == lease, self.bridgedWebView === ownedView else {
                    binding?.complete(callback: callback)
                    self?.suspendForLifecycle()
                    return
                }
                ownedView.evaluateJavaScript("void 0") { [weak self, weak binding] _, error in
                    guard let self, let binding else { return }
                    guard error == nil, binding.isCurrent, binding.lease == lease,
                          self.bridgedWebView === ownedView else {
                        binding.complete(callback: callback)
                        self.suspendForLifecycle()
                        return
                    }
                    self.completedReplyCount += 1
                    binding.complete(callback: callback)
                }
            }
        }
    }

    func suspendForLifecycle() {
        guard state != .suspended else { return }
        session?.revoke()
        messageGate?.revoke()
        session?.coordinator.suspend()
        state = .suspended
        webView?.stopLoading()
        webView?.isHidden = true
        for observation in observations { NotificationCenter.default.removeObserver(observation) }
        observations.removeAll()
    }

    deinit {
        session?.revoke()
        messageGate?.revoke()
        for observation in observations { NotificationCenter.default.removeObserver(observation) }
    }
}
