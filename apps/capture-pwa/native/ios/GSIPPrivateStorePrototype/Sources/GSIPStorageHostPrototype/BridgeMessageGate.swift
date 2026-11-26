// SPDX-License-Identifier: MIT
import Foundation
import WebKit
import Capacitor
import GSIPStorageCore

/// The wire format carries no owner, session, path, SQL, namespace or lease authority.
struct PrototypeWireRequest: Equatable {
    let method: String
    let store: LogicalStore?
    let operationID: String?
    let expectedRevision: UInt64?
    let canary: String?

    static func parse(method: String, options: [String: Any]) -> PrototypeWireRequest? {
        let expectedKeys: Set<String>
        switch method {
        case "status": expectedKeys = []
        case "read": expectedKeys = ["store"]
        case "put": expectedKeys = ["store", "operationID", "expectedRevision", "canary"]
        case "remove": expectedKeys = ["store", "operationID", "expectedRevision"]
        case "clear": expectedKeys = ["operationID"]
        default: return nil
        }
        guard Set(options.keys) == expectedKeys,
              JSONSerialization.isValidJSONObject(options),
              let encoded = try? JSONSerialization.data(withJSONObject: options),
              encoded.count <= StorageLimits.frameBytes else { return nil }
        var store: LogicalStore?
        if expectedKeys.contains("store") {
            guard let name = options["store"] as? String,
                  let parsed = LogicalStore(rawValue: name), parsed.isPayload else { return nil }
            store = parsed
        }
        var operationID: String?
        if expectedKeys.contains("operationID") {
            guard let value = options["operationID"] as? String,
                  StorageLimits.validIdentifier(value) else { return nil }
            operationID = value
        }
        var revision: UInt64?
        if expectedKeys.contains("expectedRevision") {
            guard let number = options["expectedRevision"] as? NSNumber,
                  String(cString: number.objCType) != "c",
                  number.doubleValue.isFinite, number.doubleValue >= 0,
                  number.doubleValue <= Double(StorageLimits.maxCounter),
                  number.doubleValue.rounded(.towardZero) == number.doubleValue else { return nil }
            revision = number.uint64Value
        }
        var canary: String?
        if method == "put" {
            guard let value = options["canary"] as? String,
                  value == "alpha" || value == "beta" else { return nil }
            canary = value
        }
        return PrototypeWireRequest(method: method, store: store, operationID: operationID,
                                    expectedRevision: revision, canary: canary)
    }
}

/// Replaces the sole upstream `bridge` registration before WKWebView construction.
/// Only an admitted call is forwarded; the upstream handler never sees rejected bodies.
final class BridgeMessageGate: NSObject, WKScriptMessageHandler {
    static let pluginID = "GSIPStoragePrototype"
    weak var expectedWebView: WKWebView?
    private let isCurrent: () -> Bool
    private let forward: (WKUserContentController, WKScriptMessage) -> Void
    private let admit: (String, PrototypeWireRequest) -> Bool
    private(set) var acceptedCount = 0
    private(set) var rejectedCount = 0
    private var revoked = false

    init(isCurrent: @escaping () -> Bool,
         admit: @escaping (String, PrototypeWireRequest) -> Bool = { _, _ in true },
         forward: @escaping (WKUserContentController, WKScriptMessage) -> Void) {
        self.isCurrent = isCurrent
        self.admit = admit
        self.forward = forward
        super.init()
    }

    func revoke() { revoked = true }

    func permits(body: Any, name: String, isMainFrame: Bool, scheme: String,
                 host: String, port: Int, isOwnedWebView: Bool) -> Bool {
        guard !revoked, isCurrent(), name == "bridge", isOwnedWebView, isMainFrame,
              scheme == "capacitor", host == "localhost", port == 0,
              let dictionary = body as? [String: Any],
              Set(dictionary.keys) == ["type", "pluginId", "methodName", "callbackId", "options"],
              dictionary["type"] as? String == "message",
              dictionary["pluginId"] as? String == Self.pluginID,
              let method = dictionary["methodName"] as? String,
              let callback = dictionary["callbackId"] as? String,
              StorageLimits.validIdentifier(callback), callback.utf8.count <= 64,
              let options = dictionary["options"] as? [String: Any],
              JSONSerialization.isValidJSONObject(dictionary),
              let encoded = try? JSONSerialization.data(withJSONObject: dictionary),
              encoded.count <= StorageLimits.frameBytes,
              PrototypeWireRequest.parse(method: method, options: options) != nil else { return false }
        return isCurrent()
    }

    func userContentController(_ userContentController: WKUserContentController,
                               didReceive message: WKScriptMessage) {
        let origin = message.frameInfo.securityOrigin
        guard permits(body: message.body, name: message.name,
                      isMainFrame: message.frameInfo.isMainFrame,
                      scheme: origin.protocol, host: origin.host, port: origin.port,
                      isOwnedWebView: message.webView === expectedWebView) else {
            rejectedCount += 1
            return
        }
        guard let dictionary = message.body as? [String: Any],
              let callback = dictionary["callbackId"] as? String,
              let method = dictionary["methodName"] as? String,
              let options = dictionary["options"] as? [String: Any],
              let request = PrototypeWireRequest.parse(method: method, options: options),
              admit(callback, request) else { rejectedCount += 1; return }
        acceptedCount += 1
        forward(userContentController, message)
    }
}
