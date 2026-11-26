// SPDX-License-Identifier: MIT
import Foundation
import WebKit
import Capacitor
import GSIPStorageCore

/// Does not call super.start: upstream's special file route precedes its router.
final class AssetRequestGate: WebViewAssetHandler {
    enum Decision: Equatable { case bundled(String), canary(String), denied }
    private let isCurrent: () -> Bool
    private let broker: OwnedTemporaryPhotoBroker?

    init(isCurrent: @escaping () -> Bool, broker: OwnedTemporaryPhotoBroker? = nil) {
        self.isCurrent = isCurrent
        self.broker = broker
        super.init(router: CapacitorRouter())
    }

    func decision(for request: URLRequest) -> Decision {
        guard isCurrent(), request.httpMethod == "GET", request.httpBody == nil,
              request.value(forHTTPHeaderField: "Range") == nil,
              request.value(forHTTPHeaderField: "Cookie") == nil,
              request.value(forHTTPHeaderField: "Authorization") == nil,
              let url = request.url,
              let parts = URLComponents(url: url, resolvingAgainstBaseURL: false),
              parts.scheme == "capacitor", parts.host == "localhost", parts.port == nil,
              parts.user == nil, parts.password == nil, parts.query == nil, parts.fragment == nil else { return .denied }
        let path = parts.percentEncodedPath
        if path == "/index.html" { return .bundled("index.html") }
        if path == "/gsip-activation.json" { return .bundled("gsip-activation.json") }
        let prefix = "/gsip-canary/"
        if path.hasPrefix(prefix) {
            let handle = String(path.dropFirst(prefix.count))
            if handle.count == 64 && handle.utf8.allSatisfy({ ($0 >= 48 && $0 <= 57) || ($0 >= 97 && $0 <= 102) }),
               broker?.contains(handle: handle) == true { return .canary(handle) }
        }
        return .denied
    }

    func bundledBytes(_ name: String) throws -> Data {
        guard name == "index.html" || name == "gsip-activation.json",
              let root = Bundle.main.resourceURL?.appendingPathComponent("public", isDirectory: true) else { throw StorageHold.boundary }
        let url = root.appendingPathComponent(name, isDirectory: false)
        let rootValues = try root.resourceValues(forKeys: [.isSymbolicLinkKey, .isDirectoryKey])
        let values = try url.resourceValues(forKeys: [.isSymbolicLinkKey, .isRegularFileKey, .fileSizeKey])
        guard rootValues.isSymbolicLink == false, rootValues.isDirectory == true,
              values.isSymbolicLink == false, values.isRegularFile == true,
              let size = values.fileSize, size > 0, size <= StorageLimits.frameBytes,
              url.resolvingSymlinksInPath() == url.standardizedFileURL else { throw StorageHold.boundary }
        let bytes = try Data(contentsOf: url)
        guard bytes.count == size else { throw StorageHold.boundary }
        return bytes
    }

    override func webView(_ webView: WKWebView, start urlSchemeTask: WKURLSchemeTask) {
        do {
            let bytes: Data
            let mime: String
            switch decision(for: urlSchemeTask.request) {
            case let .bundled(name): bytes = try bundledBytes(name); mime = name.hasSuffix(".html") ? "text/html" : "application/json"
            case let .canary(handle):
                guard let broker else { throw StorageHold.boundary }
                bytes = try broker.read(handle: handle); mime = "application/octet-stream"
            case .denied: throw StorageHold.boundary
            }
            guard isCurrent(), let url = urlSchemeTask.request.url,
                  let response = HTTPURLResponse(url: url, statusCode: 200, httpVersion: nil, headerFields: [
                    "Content-Type": mime,
                    "Cache-Control": "no-store",
                    "Content-Security-Policy": "default-src 'none'; script-src 'self'; connect-src 'none'; frame-src 'none'; base-uri 'none'; form-action 'none'"
                  ]) else { throw StorageHold.staleLease }
            urlSchemeTask.didReceive(response)
            urlSchemeTask.didReceive(bytes)
            urlSchemeTask.didFinish()
        } catch { urlSchemeTask.didFailWithError(StorageHold.boundary) }
    }

    override func webView(_ webView: WKWebView, stop urlSchemeTask: WKURLSchemeTask) { }
}
