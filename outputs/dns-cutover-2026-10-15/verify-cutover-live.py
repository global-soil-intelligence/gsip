"""Read-only verification of the approved Pages artifact at its canonical domain."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
import json
import socket
import ssl


OUT = Path(__file__).resolve().parent
EXPECTED = json.loads(
    (OUT.parent / "merge-75-pages-2026-10-15/artifact-verification.json").read_text()
)
BASE = "https://globalsoilintelligence.com/"
HEADERS = {
    "User-Agent": "GSIP-owner-authorized-DNS-cutover-verification/1.0",
    "Cache-Control": "no-cache",
    "Accept-Encoding": "identity",
}
ALLOWED_HOSTS = {
    "globalsoilintelligence.com",
    "www.globalsoilintelligence.com",
    "global-soil-intelligence.github.io",
}


class RedirectTrace(HTTPRedirectHandler):
    def __init__(self):
        self.chain = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urlparse(newurl)
        if target.scheme not in {"https", "http"} or target.hostname not in ALLOWED_HOSTS:
            raise ValueError("Unexpected redirect destination")
        if urlparse(req.full_url).scheme == "https" and target.scheme != "https":
            raise ValueError("HTTPS redirect downgrade")
        self.chain.append({"from": req.full_url, "status": code, "to": newurl})
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url):
    trace = RedirectTrace()
    opener = build_opener(trace)
    with opener.open(Request(url, headers=HEADERS), timeout=25) as response:
        raw = response.read(10 * 1024 * 1024)
        return {
            "requested_url": url,
            "final_url": response.url,
            "status": response.status,
            "bytes": len(raw),
            "sha256": sha256(raw).hexdigest(),
            "content_type": response.headers.get("Content-Type"),
            "redirects": trace.chain,
        }, raw


def file_check(item):
    result = {"path": item["path"], "matches_approved_artifact": False}
    try:
        fetched, raw = fetch(BASE + quote(item["path"], safe="/"))
        result.update(fetched)
        result["matches_approved_artifact"] = (
            fetched["status"] == 200
            and fetched["sha256"] == item["sha256"]
            and fetched["bytes"] == item["bytes"]
            and urlparse(fetched["final_url"]).scheme == "https"
            and urlparse(fetched["final_url"]).hostname == "globalsoilintelligence.com"
        )
        if item["path"] == "capture/gsip-activation.json":
            activation = json.loads(raw)
            result["activation"] = activation
            result["closed_flags_verified"] = (
                set(activation) == {"capture_live", "library_intake_live"}
                and all(type(v) is bool and v is False for v in activation.values())
            )
    except Exception as error:
        result["error_type"] = type(error).__name__
        if isinstance(error, HTTPError):
            result["status"] = error.code
    return result


def route_check(pair):
    url, destination = pair
    try:
        result, _ = fetch(url)
        result["expected_destination"] = destination
        result["pass"] = result["status"] == 200 and result["final_url"] == destination
        if url != destination:
            result["pass"] = result["pass"] and bool(result["redirects"])
        return result
    except Exception as error:
        return {"requested_url": url, "error_type": type(error).__name__, "pass": False}


def certificate_check(host):
    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=20) as tcp:
            with context.wrap_socket(tcp, server_hostname=host) as connection:
                cert = connection.getpeercert()
                return {
                    "hostname": host,
                    "trusted_and_hostname_valid": True,
                    "tls_version": connection.version(),
                    "not_before": cert.get("notBefore"),
                    "not_after": cert.get("notAfter"),
                    "subject_alt_names": cert.get("subjectAltName"),
                    "issuer": cert.get("issuer"),
                }
    except Exception as error:
        return {"hostname": host, "trusted_and_hostname_valid": False,
                "error_type": type(error).__name__}


if __name__ == "__main__":
    started = datetime.now(timezone.utc)
    with ThreadPoolExecutor(max_workers=6) as pool:
        files = list(pool.map(file_check, EXPECTED["files"]))
    routes_to_check = [
        (BASE, BASE),
        ("http://globalsoilintelligence.com/", BASE),
        ("https://www.globalsoilintelligence.com/", BASE),
        ("http://www.globalsoilintelligence.com/", BASE),
        ("https://global-soil-intelligence.github.io/gsip/", BASE),
        ("https://global-soil-intelligence.github.io/gsip/data/", BASE + "data/"),
        ("https://global-soil-intelligence.github.io/gsip/og-library.png", BASE + "og-library.png"),
        ("https://www.globalsoilintelligence.com/data/", BASE + "data/"),
    ]
    with ThreadPoolExecutor(max_workers=4) as pool:
        routes = list(pool.map(route_check, routes_to_check))
        certificates = list(pool.map(certificate_check, [
            "globalsoilintelligence.com", "www.globalsoilintelligence.com"
        ]))
    activation = next(r for r in files if r["path"] == "capture/gsip-activation.json")
    matched = sum(r["matches_approved_artifact"] for r in files)
    passed = (
        matched == len(EXPECTED["files"])
        and activation.get("closed_flags_verified") is True
        and all(r["pass"] for r in routes)
        and all(c["trusted_and_hostname_valid"] for c in certificates)
    )
    receipt = {
        "status": "LIVE_ARTIFACT_HTTPS_REDIRECTS_AND_CLOSED_FLAGS_PASS" if passed
        else "NOT_YET_FULLY_VERIFIED",
        "checked_at_utc": started.isoformat(),
        "base_url": BASE,
        "approved_run": 38821460183,
        "approved_source_commit": EXPECTED["source_commit"],
        "approved_artifact_sha256": EXPECTED["zip_sha256"],
        "files_matching": matched,
        "files_expected": len(EXPECTED["files"]),
        "activation": activation.get("activation"),
        "files": files,
        "routes": routes,
        "certificates": certificates,
        "mutations": "NONE; GET and TLS handshakes only; certificate validation enabled",
    }
    target = OUT / ("cutover-live-verification-" + started.strftime("%Y%m%dT%H%M%SZ") + ".json")
    target.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: receipt[k] for k in [
        "status", "checked_at_utc", "files_matching", "files_expected", "activation"
    ]}, indent=2))
    print(str(target))
    raise SystemExit(0 if passed else 1)
