## Work package

- WP: WP-AGENT-1, agent-readable GSIP (`docs/BUILD_ORDER.md` §4, Phase 1.5)
- Branch: `wp-agent-1-read-api`
- Stacked on (if any): `wp-6e-provenance`

## Summary

GSIP's read interfaces for people and agents (SPEC section 9).

- **`gsip-public` Edge Function** (`verify_jwt = false`).
  - **REST under `/v1`:** protocol, a cell, cells within an area (paged), the latest release, and
    OpenAPI 3.1.
  - **A stateless MCP server at `/mcp`** with `get_protocol`, `get_cell`, `list_cells` and
    `get_release`. It supports the 2026-07-28 revision (per-request `_meta`, mirrored headers,
    `server/discover`) and the `initialize` handshake of 2025-11-25, 2025-06-18 and 2025-03-26.
    It never mints a session.
- **I12.** The function reads PostgREST with the project's publishable key only; any other key is
  refused. Rows are validated and unknown columns dropped. Text people wrote is returned only
  inside `untrusted` fields.
- **I7 by design.**
  - Withheld and empty cells answer alike.
  - Cells finer than resolution 8 are refused, so a question never reveals more about the asker
    than GSIP publishes.
- **Every answer** carries licence, attribution, citation and notice fields.
- **Rate limits.** A per-client token bucket, keyed on the connecting address, with a per-instance
  ceiling. URLs in answers never come from forwarded headers.
- **`dataset_releases`.** A public, append-only record of each pushed commit. The export writes it
  last and idempotently.
- **Site.**
  - Every page is prerendered and hydrated, and carries Organization JSON-LD; the home and data
    pages also carry Dataset JSON-LD.
  - The build fails without them.
  - `llms.txt` is published at the root.
  - `docs/AGENTS.md` is the guide for agent builders.

## Acceptance criteria

- [x] vitest (schema): REST validation, public fields only, withheld equals empty; MCP version
      negotiation, four tools with JSON Schemas, structured and text content, JSON-RPC errors, and
      202 for notifications; untrusted fencing.
- [x] pgTAP `wp_agent1_public` (12): the anonymous role reads `dataset_releases` and `h3_cells` and
      nothing private. A test fails if the function source references the service role.
- [x] Build check and e2e `agent-readable`: every page carries its headline and JSON-LD without
      JavaScript, and `llms.txt` is at the root.
- [x] Local lint, typecheck, test, build and database tests pass (see Verification evidence).

## Invariant impact

- [x] I7: no finer-than-published questions are answered, and withheld cells are indistinguishable
      from empty ones.
- [x] I12: publishable-key-only reads; the anonymous role's grants bound everything.
- [x] I14: per-client and per-instance limits.

## Business guardrails

- [x] B1: the read API is free, and its data is released under ODbL and CC BY-SA with the
      obligations stated correctly. B5: no tracking, and request logs are disclosed.

## Agent contribution

- [x] Written by Claude (Claude Opus 5.5), named in `Co-Authored-By` trailers. An independent agent
      review followed, fixed in `f20d793`. It checked the H3 range maths exhaustively (6.59 million
      checks, pentagons included) and ran end to end against real PostgREST, the MCP Inspector, and
      SDK v1 and v2 clients.

Human of record: Justin Hart. **Sign-off pending:** an agent never certifies the DCO.

## Dependencies and deviations

None added; the function reuses `packages/schema`.

**Decisions:**

- Refusing cells finer than resolution 8.
- The per-instance ceiling.
- Publishable-key-only reads.

All three follow from I7, I12 and I14. Confirm them before the function is deployed publicly.

## Verification evidence

Run locally on `f20d793`, 2026-10-11:

- `pnpm lint` and `pnpm typecheck` pass.
- vitest: schema 126, site 28, map 15, capture 96.
- ruff, mypy (31 files) and pytest (202) pass.
- pgTAP: prior_attempts 30/30, rls 42/42, wp6b_integrity 51/51, wp6d_rights 70/70, wp6e_provenance 57/57, wp_agent1_public 12/12.
- Migration test: 13/13. `deno check` passes.
- Playwright runs in CI on this pull request; at the stack's tip it passes 24/24 (desktop and mobile Chrome).

## Independent review and resolutions

Verdict: "meets its acceptance criteria; nothing blocks merge", with M-1 to be fixed before public
deployment. All findings are fixed.

| ID   | Severity | Finding                                                                                                        | Resolution                                                                                                                     |
| ---- | -------- | -------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| M-1  | Major    | The 64 KiB MCP body limit was checked only after buffering the whole body; three 200 MB POSTs peaked at 1.5 GB | A declared oversize body is refused before reading; an undeclared body is cancelled at the limit; decoded once as strict UTF-8 |
| m-2  | Minor    | `unique (version, hf_revision)` treated NULLs as distinct, so retries duplicated a push without a commit id    | `unique nulls not distinct (version, hf_revision)`                                                                             |
| m-3  | Minor    | A message with an id but no usable method got 202 and no body                                                  | 400 with JSON-RPC -32600, echoing its id; only real responses get 202                                                          |
| m-4  | Minor    | Pagination tests ran against a fake that re-implemented the query semantics                                    | Tests pin the exact PostgREST query, `next` on a full last page, and `no-store` on errors                                      |
| m-5  | Minor    | The privacy notice said request addresses and cells are never stored, but gateway logs keep both               | The notice says plainly what hosting request logs keep                                                                         |
| m-6  | Minor    | The agent guide overstated share-alike                                                                         | ODbL obligations stated correctly: share-alike for databases, a notice for produced works                                      |
| m-7  | Minor    | Dataset JSON-LD declared ODbL only and labelled an HTML page as a download                                     | Both licences declared; no false distribution                                                                                  |
| m-8  | Minor    | Callers without an address shared one bucket                                                                   | They are not pooled; only the instance ceiling applies                                                                         |
| m-9  | Minor    | `Origin: null` and non-http origins got 403 from `/mcp`                                                        | Any well-formed Origin is served; only a malformed header is refused                                                           |
| n-10 | Nit      | A blank `GSIP_PUBLIC_BASE_URL` let the Host header set URLs in cacheable answers                               | `agent/config.ts` treats blank values as unset, so URLs always come from configuration                                         |

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_017nrzCzGuaW3XpYuuvMm7U1
