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


## Changes after review

- Justin approved exactly three historical synthetic-fixture fingerprints as a documented exception on 2026-10-11. CI scans every branch, so every branch needs the same file. The four-line `.gitleaksignore` starts in commit `afadda9` on `docs/spec-v3` and is merged forward unchanged.
- `.gitleaks.toml`, all detection rules, redaction, full-history scanning and the secret-scan workflow remain unchanged. No further suppression is authorized. No dependency added.
- Owning-branch fixture cleanup `5e50028` constructs dummy publishable/secret-format keys and an unsigned anonymous JWT instead of long literal credentials. Existing assertions are unchanged: secret-format keys and privileged JWT roles are still refused; default and mobile fixtures remain distinct. This cleanup was merged forward to WP-APP-1.
- Verification: all 16 targeted agent tests, schema typecheck, ESLint and formatting passed. With exact Gitleaks 8.21.2 each original fixture source failed (one match), each cleaned source passed (zero matches), staged changes passed, and the complete stack passed: **69 commits scanned, no leaks found, exit code 0**. GitHub current-head checks are pending.
- Assumptions: the historical values are synthetic mocked test fixtures, and generated values are deliberately nonfunctional test data. This exception applies only to the three approved immutable fingerprints; new matching commits still fail. Capture stays closed and no production deployment or merge was performed.


### Current-head CI completed

At `5e50028`, [validate](https://github.com/global-soil-intelligence/gsip/actions/runs/38189450932/job/114618848348) and [Gitleaks](https://github.com/global-soil-intelligence/gsip/actions/runs/38189450894/job/114618848363) completed successfully. DCO was intentionally skipped for this same-repository PR; no agent supplied a human sign-off. This completed result supersedes the pending-CI notes above.


### Security-boundary correction and exact-head CI (2026-10-12)

Current head: `f156ad9d886975f879beb525f384fed5fc490894`. Existing description and earlier verification records are preserved above.

Inherited change: merge-forward carries #28’s spec-first boundary clarification and #29/#31’s additive guarded-helper/invoker and restrictive-policy fixes. The owning fixes remain on WP-6b/WP-6d; this branch does not duplicate or rewrite their SQL.

The hosted Gate C zero-findings check stopped on seven findings across the service-only rights tables and client-executable public definer functions. The correction preserves authorization rather than suppressing any advisor rule. All 26 executed migration blobs remain unchanged. No new client schema, table or column grant is added; narrow EXECUTE grants on new private helpers match the existing public callers. Public signatures and caller ACLs, owner checks, withdrawal refusal and capture-closed behavior remain intact.

Local source proof preserved the existing WP-6b 99 assertions and WP-6d 209 assertions; the new owning suites passed 16 and 21 assertions respectively, with 13 new assertions failing before the changes. The candidate complete pgTAP suite passed 299 assertions, migration testing passed 13/13, and isolated synthetic PostgREST dispatch/reload/privilege tests passed 33/33. These are local proofs; hosted advisor remediation remains unexecuted.

Exact-head CI, verified 2026-10-12 14:56:50 UTC: [validate — SUCCESS](https://github.com/global-soil-intelligence/gsip/actions/runs/38265397149/job/114866165331), [gitleaks — SUCCESS](https://github.com/global-soil-intelligence/gsip/actions/runs/38265397056/job/114866163762). All 13 updated PR heads are green for their required checks. DCO is SKIPPED; an agent has not certified Justin’s DCO.

Assumptions: the reviewed migration owner and exposed-schema settings remain unchanged and there is no overlapping production writer; production execution must refresh these checks. Private is absent from the observed Data API exposed-schema list, but schema placement alone is not authorization. Local tests use synthetic data and do not establish the hosted advisor’s final state. Capture, sign-up and anonymous sign-in stay closed; no production mutation, deployment, new dependency, service or licence change is included in this update.


### Changes after review — owner merge exception and worker holds (2026-10-12)

Justin explicitly authorised removing the extra approving-review requirement for this owner-operated repository. Independent review, green CI, resolved conversations and protection against force pushes remain required. Agents do not submit approving reviews or certify the DCO.
Scheduled production workers now require their own explicit repository-variable opt-in; absent variables hold jobs before any secret-bearing step. Manual dispatch still requires a separate production gate. Contributor-rights schedules receive the same hold from WP-6d onward. This prevents merging workflows or adding a credential from starting unapproved production work. Regression tests failed before the relevant change and passed after it.

Assumptions: schedule opt-in variables remain unset; this merge authority does not authorise deployments, worker dispatches or capture opening. No dependencies or secret-scan exceptions were added.
