from __future__ import annotations
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen
BASE = "https://toxldjgwkxtneoqsazym.supabase.co/functions/v1"

def request(path: str, expected: int, data: dict[str, object] | None = None, headers: dict[str, str] | None = None) -> bytes:
    payload = json.dumps(data).encode() if data is not None else None
    req = Request(BASE + path, data=payload, headers=headers or {})
    try:
        with urlopen(req, timeout=30) as response:
            status, body = response.status, response.read(262145)
    except HTTPError as error:
        status, body = error.code, error.read(262145)
    print(json.dumps({"path": path, "http_status": status, "expected": expected}))
    if status != expected or len(body) > 262144:
        raise SystemExit("Unexpected status or oversized response; stop without printing body")
    return body

request("/prior-attach", 401)
protocol = json.loads(request("/gsip-public/v1/protocol", 200))
if not isinstance(protocol, dict) or not isinstance(protocol.get("data"), dict):
    raise SystemExit("Protocol response must carry the expected object envelope")
license_fields = protocol.get("license", {})
if not isinstance(license_fields, dict) or any(license_fields.get(k) != v for k, v in {"data": "ODbL-1.0", "photos": "CC-BY-SA-4.0", "code": "MIT"}.items()):
    raise SystemExit("Protocol license fields do not match the reviewed contract")
citation = protocol.get("citation", {})
if not isinstance(citation, dict) or not all(isinstance(citation.get(k), str) and citation[k].strip() for k in ("text", "bibtex")):
    raise SystemExit("Protocol citation fields are missing")
print(json.dumps({"protocol_license_and_citation_fields": "PASS"}))
request("/gsip-public/v1/cells/892a8ab5863ffff", 400)
result = json.loads(request("/gsip-public/mcp", 200,
    {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {"_meta": {"io.modelcontextprotocol/protocolVersion": "2026-07-28"}}},
    {"Content-Type": "application/json", "Accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2026-07-28", "Mcp-Method": "tools/list"}))
tools = result.get("result", {}).get("tools", [])
expected_tools = {"get_protocol", "get_cell", "list_cells", "get_release"}
if not isinstance(tools, list) or len(tools) != 4 or {tool.get("name") for tool in tools} != expected_tools:
    raise SystemExit("MCP must list exactly the four reviewed tools; stop without printing body")
if not all(tool.get("annotations", {}).get("readOnlyHint") is True and tool.get("annotations", {}).get("destructiveHint") is False for tool in tools):
    raise SystemExit("MCP tool annotations must remain read-only and nondestructive")
print(json.dumps({"mcp_tool_count": len(tools), "status": "READONLY_SMOKES_PASSED", "jwt_metadata_confirmation_still_required": True}))
