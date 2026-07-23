"""Prepared Gate E HTTP checks: anonymous, fixed target, no deployment or credentials."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import unittest
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

PROJECT = "toxldjgwkxtneoqsazym"
BASE = f"https://{PROJECT}.supabase.co/functions/v1"
MAX_BODY = 262144
FINE_FIXTURE = "892a8ab5863ffff"  # Existing runbook fixture, not contributor data.
COARSE_FIXTURE = "882a8ab587fffff"  # Its resolution-8 parent.
TOOLS = {"get_protocol", "get_cell", "list_cells", "get_release"}
LICENSE = {"data": "ODbL-1.0", "photos": "CC-BY-SA-4.0", "code": "MIT"}
Transport = Callable[[Request], tuple[int, bytes]]


class Mismatch(Exception):
    """Only safe check names/reasons are exposed; never response contents."""


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str,
                         headers: Any, newurl: str) -> None:
        return None


def transport(request: Request) -> tuple[int, bytes]:
    try:
        with build_opener(NoRedirects()).open(request, timeout=30) as response:
            return response.status, response.read(MAX_BODY + 1)
    except HTTPError as error:
        return error.code, error.read(MAX_BODY + 1)
    except (URLError, TimeoutError, OSError) as error:
        raise Mismatch("transport unavailable; no retry or response output") from error


def require(condition: bool, detail: str) -> None:
    if not condition:
        raise Mismatch(detail)


def envelope(value: Any) -> dict[str, Any]:
    require(isinstance(value, dict) and isinstance(value.get("data"), dict),
            "public envelope is missing")
    require(isinstance(value.get("license"), dict) and
            all(value["license"].get(k) == v for k, v in LICENSE.items()),
            "public licences mismatch")
    citation = value.get("citation")
    require(isinstance(citation, dict) and
            all(isinstance(citation.get(k), str) and citation[k].strip()
                for k in ("text", "bibtex")), "public citation missing")
    return value["data"]


def run(phase: str, send: Transport = transport) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    def request(label: str, path: str, status: int,
                payload: dict[str, Any] | None = None,
                headers: dict[str, str] | None = None,
                parse: bool = False) -> Any:
        request_headers = {"Accept": "application/json"}
        request_headers.update(headers or {})
        require(not any(k.lower() in ("authorization", "apikey", "cookie")
                        for k in request_headers), "credential header refused")
        data = json.dumps(payload).encode() if payload is not None else None
        if data is not None:
            request_headers["Content-Type"] = "application/json"
        req = Request(BASE + path, data=data, headers=request_headers,
                      method="POST" if data is not None else "GET")
        observed, body = send(req)
        require(observed == status, f"{label}: HTTP {observed}, expected {status}")
        require(len(body) <= MAX_BODY, f"{label}: oversized response")
        results.append({"check": label, "http_status": observed,
                        "expected_status": status, "response_sha256":
                        hashlib.sha256(body).hexdigest()})
        if not parse:
            return None
        try:
            return json.loads(body)
        except (ValueError, UnicodeError) as error:
            raise Mismatch(f"{label}: malformed JSON") from error

    # Empty unauthenticated POST never supplies a submission id or enters a prior job.
    request("prior_unauthenticated_denied", "/prior-attach", 401, {})
    if phase == "prior":
        return results

    protocol = envelope(request("protocol", "/gsip-public/v1/protocol",
                                200, parse=True))
    require(bool(protocol), "protocol data empty")
    fine = request("resolution9_refused",
                   f"/gsip-public/v1/cells/{FINE_FIXTURE}", 400, parse=True)
    require(isinstance(fine, dict) and isinstance(fine.get("error"), str) and
            "resolution 8" in fine["error"], "fine-cell refusal contract mismatch")

    response = request("mcp_four_tools", "/gsip-public/mcp", 200,
                       {"jsonrpc": "2.0", "id": 1, "method": "tools/list",
                        "params": {"_meta": {
                            "io.modelcontextprotocol/protocolVersion": "2026-07-28"}}},
                       {"Accept": "application/json, text/event-stream",
                        "MCP-Protocol-Version": "2026-07-28",
                        "Mcp-Method": "tools/list"}, parse=True)
    require(isinstance(response, dict) and response.get("jsonrpc") == "2.0" and
            response.get("id") == 1 and isinstance(response.get("result"), dict),
            "MCP response envelope mismatch")
    tools = response["result"].get("tools")
    require(isinstance(tools, list) and len(tools) == 4 and
            all(isinstance(tool, dict) for tool in tools) and
            {tool.get("name") for tool in tools} == TOOLS, "MCP tool list mismatch")
    require(all(isinstance(tool.get("annotations"), dict) and
                tool["annotations"].get("readOnlyHint") is True and
                tool["annotations"].get("destructiveHint") is False
                for tool in tools), "MCP tools must remain read-only")

    cell = envelope(request("public_reader_empty_cell",
                            f"/gsip-public/v1/cells/{COARSE_FIXTURE}", 200,
                            parse=True))
    require(cell == {"cell": COARSE_FIXTURE, "resolution": 8,
                     "status": "no_published_observations", "published": None,
                     "containing": []}, "empty public cell contract mismatch")
    cells = envelope(request("public_reader_empty_list",
                             f"/gsip-public/v1/cells?within={COARSE_FIXTURE}&limit=1",
                             200, parse=True))
    require(cells == {"within": COARSE_FIXTURE, "cells": [], "next": None},
            "empty public list contract mismatch")
    release = envelope(request("public_reader_no_release",
                               "/gsip-public/v1/releases/latest", 200, parse=True))
    require(release == {"release": None}, "empty public release contract mismatch")
    request("public_write_method_refused", "/gsip-public/v1/protocol", 405, {})
    return results


def fake_responses() -> dict[str, tuple[int, bytes]]:
    def packed(data: Any) -> bytes:
        return json.dumps(data).encode()

    def wrapped(data: Any) -> bytes:
        return packed({"data": data, "license": LICENSE,
                       "citation": {"text": "Synthetic GSIP citation",
                                    "bibtex": "@misc{synthetic}"}})

    return {
        "/prior-attach": (401, packed({"error": "Authentication required"})),
        "/gsip-public/v1/protocol": (200, wrapped({"version": "fixture"})),
        f"/gsip-public/v1/cells/{FINE_FIXTURE}":
            (400, packed({"error": "cell must be at resolution 8 or coarser"})),
        "/gsip-public/mcp": (200, packed({"jsonrpc": "2.0", "id": 1,
            "result": {"tools": [{"name": name, "annotations":
                {"readOnlyHint": True, "destructiveHint": False}}
                for name in sorted(TOOLS)]}})),
        f"/gsip-public/v1/cells/{COARSE_FIXTURE}":
            (200, wrapped({"cell": COARSE_FIXTURE, "resolution": 8,
                          "status": "no_published_observations",
                          "published": None, "containing": []})),
        f"/gsip-public/v1/cells?within={COARSE_FIXTURE}&limit=1":
            (200, wrapped({"within": COARSE_FIXTURE, "cells": [], "next": None})),
        "/gsip-public/v1/releases/latest": (200, wrapped({"release": None})),
    }


class SmokeTests(unittest.TestCase):
    def fake(self, responses: dict[str, tuple[int, bytes]]) -> Transport:
        def send(req: Request) -> tuple[int, bytes]:
            self.assertTrue(req.full_url.startswith(BASE + "/"))
            self.assertFalse(any(k.lower() in ("authorization", "apikey", "cookie")
                                 for k in req.headers))
            path = req.full_url.removeprefix(BASE)
            if path == "/prior-attach":
                self.assertEqual(json.loads(req.data or b"null"), {})
            if path == "/gsip-public/v1/protocol" and req.method == "POST":
                return 405, b'{"error":"Method not allowed"}'
            return responses[path]
        return send

    def reject(self, path: str, status: int, body: bytes) -> None:
        responses = fake_responses()
        responses[path] = (status, body)
        with self.assertRaises(Mismatch):
            run("all", self.fake(responses))

    def test_all_expected_contracts(self) -> None:
        self.assertEqual(len(run("all", self.fake(fake_responses()))), 8)

    def test_prior_phase_cannot_call_public_or_jobs(self) -> None:
        self.assertEqual(len(run("prior", self.fake(fake_responses()))), 1)

    def test_prior_jwt_denial_required(self) -> None:
        self.reject("/prior-attach", 200, b"{}")

    def test_protocol_status_required(self) -> None:
        self.reject("/gsip-public/v1/protocol", 503, b"{}")

    def test_protocol_licence_required(self) -> None:
        value = json.loads(fake_responses()["/gsip-public/v1/protocol"][1])
        value["license"]["data"] = "invalid-fixture"
        self.reject("/gsip-public/v1/protocol", 200, json.dumps(value).encode())

    def test_protocol_citation_required(self) -> None:
        value = json.loads(fake_responses()["/gsip-public/v1/protocol"][1])
        del value["citation"]["bibtex"]
        self.reject("/gsip-public/v1/protocol", 200, json.dumps(value).encode())

    def test_fine_cell_cannot_succeed(self) -> None:
        self.reject(f"/gsip-public/v1/cells/{FINE_FIXTURE}", 200, b"{}")

    def test_four_tools_required(self) -> None:
        value = json.loads(fake_responses()["/gsip-public/mcp"][1])
        value["result"]["tools"].pop()
        self.reject("/gsip-public/mcp", 200, json.dumps(value).encode())

    def test_tools_cannot_be_destructive(self) -> None:
        value = json.loads(fake_responses()["/gsip-public/mcp"][1])
        value["result"]["tools"][0]["annotations"]["destructiveHint"] = True
        self.reject("/gsip-public/mcp", 200, json.dumps(value).encode())

    def test_reader_failure_stops(self) -> None:
        self.reject("/gsip-public/v1/releases/latest", 503, b"{}")

    def test_unexpected_published_cell_stops(self) -> None:
        value = json.loads(fake_responses()[f"/gsip-public/v1/cells/{COARSE_FIXTURE}"][1])
        value["data"]["status"] = "published"
        self.reject(f"/gsip-public/v1/cells/{COARSE_FIXTURE}", 200,
                    json.dumps(value).encode())

    def test_malformed_json_stops(self) -> None:
        self.reject("/gsip-public/v1/protocol", 200, b"not-json")

    def test_oversized_response_stops(self) -> None:
        self.reject("/gsip-public/v1/protocol", 200, b"x" * (MAX_BODY + 1))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("prior", "all"), default="all")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        result = unittest.TextTestRunner(verbosity=1).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(SmokeTests))
        raise SystemExit(0 if result.wasSuccessful() else 1)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        results = run(args.phase)
    except Mismatch as error:
        print(json.dumps({"state": "STOP_HTTP_SMOKE_MISMATCH",
                          "reason": str(error), "no_retry": True}))
        raise SystemExit(1)
    receipt = {"state": "PASS_HTTP_SMOKES_METADATA_SEPARATELY_REQUIRED",
               "phase": args.phase, "target": PROJECT, "started_at_utc": started,
               "completed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "checks": results, "credentials_used": False, "private_rows_read": False,
               "prior_jobs_started": False, "automatic_retries": False,
               "limits": ["HTTP denial alone cannot prove JWT verification; read function metadata.",
                          "Prior owner/service success paths are not invoked; no authenticated job smoke.",
                          "Empty-reader checks require zero public cells and zero dataset releases."]}
    path = Path(__file__).resolve().parent / (
        "gate-e-http-" + args.phase + "-" +
        datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    with path.open("x") as handle:
        handle.write(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"state": receipt["state"], "checks_passed": len(results),
                      "receipt": str(path),
                      "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()

