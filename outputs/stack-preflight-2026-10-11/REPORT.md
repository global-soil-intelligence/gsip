# GSIP stack landing and deployment preflight — October 11, 2026

State: **BLOCKED_MISSING_REVIEWED_HANDOFF**. Live observations were captured at
7:50 p.m. America/New_York. The first recovery action is to provide the absolute
path to the unzipped `gsip-stack-handoff-2026-10-11/` directory.

No reviewed branch was imported, rewritten, pushed, merged, approved, or changed.
No production migration, deployment, worker dispatch, account change, or capture
opening occurred. The only workspace additions are this operational report and
its sanitized evidence receipt. Existing local source changes were preserved.

## Phase 1

Authenticated GitHub access has push/admin permissions. Live `main` is
`7a2c082ced29a9da2e731484590ea5aedfe5a657`, matching the requested baseline.
`git ls-remote --heads origin` returned only `main`, `gh-pages`,
`chore/dependabot-grouping`, and `codex/opencore-e1-2026-09`.

| Order | Reviewed branch | Expected base | Expected head | PR link | Checks |
| --- | --- | --- | --- | --- | --- |
| 1 | `docs/spec-v3` | `main` | `e258b41` | None; branch absent | NOT_RUN |
| 2 | `wp-6b-launch-hardening` | `docs/spec-v3` | `1c4aa51` | None; branch absent | NOT_RUN |
| 3 | `wp-6c-priors-and-tiles` | `wp-6b-launch-hardening` | `f3ffa4f` | None; branch absent | NOT_RUN |
| 4 | `wp-6d-contributor-rights` | `wp-6c-priors-and-tiles` | `18c4aba` | None; branch absent | NOT_RUN |
| 5 | `wp-6e-provenance` | `wp-6d-contributor-rights` | `af336ae` | None; branch absent | NOT_RUN |
| 6 | `wp-agent-1-read-api` | `wp-6e-provenance` | `f20d793` | None; branch absent | NOT_RUN |
| 7 | `wp-app-1-phone-app` | `wp-agent-1-read-api` | `a8818aa` | None; branch absent | NOT_RUN |

GitHub lists no open PRs and zero workflow artifacts. Therefore neither the APK
nor simulator artifact exists in the repository's current artifact listing, and
the app-build acceptance box cannot be ticked. No post-review fixes were made.

Dependency cleanup is already satisfied: [#20](https://github.com/global-soil-intelligence/gsip/pull/20),
[#21](https://github.com/global-soil-intelligence/gsip/pull/21), and
[#22](https://github.com/global-soil-intelligence/gsip/pull/22) are closed;
[#24](https://github.com/global-soil-intelligence/gsip/pull/24) is merged.
No additional comments or closure actions were needed.

The existing main-head [CI run](https://github.com/global-soil-intelligence/gsip/actions/runs/37069813480)
reports success. It is baseline evidence only, not a check of any reviewed head,
and was not run by this agent. None of the requested verification suites was run
in this session. The supplied baseline counts remain historical, unverified claims.

Local source is `wp-site-public-hub` at `a581d20`, with 61 original status entries.
The requested commits are absent from the local object database. Local searches
found no matching handoff, `push-stack.sh`, or GSIP bundle in Desktop, Downloads,
Documents, temporary folders, iCloud/Mobile Documents, home archives, or hidden
agent directories. Five traversal denials affected media libraries only.

The authoritative v3 governing documents cannot be read until the handoff is
available. The live main [deployment document](https://github.com/global-soil-intelligence/gsip/blob/7a2c082ced29a9da2e731484590ea5aedfe5a657/docs/PHASE1_DEPLOYMENT.md)
is dated July 23 and references SPEC v2.2. `docs/APP_STORE.md` is absent from main.
The old contribution instructions do not override Justin's explicit prohibition
on agent DCO certification, rebasing reviewed branches, or merging PRs.

## Phase 2

These are preflight observations, not completed deployment steps. The requested
phase order remains enforced. Exact production commands and a confirmed target
will be posted only after inspecting the v3 runbook and migration plan; Justin's
explicit **go** is required before each production migration/deployment.

| Step | State | Evidence / recovery |
| --- | --- | --- |
| Production selection | JUSTIN_ACTION | Supabase `get_project` returned `toxldjgwkxtneoqsazym`, name `gsip`, region `us-east-1`, status `INACTIVE`, PostgreSQL `17.6.1.147`. Name matches; production approval and tier are unconfirmed. No restore was attempted. |
| Database migration | BLOCKED | Phase 1 and v3 source unavailable; target inactive. No `db push` or migration test run. Migration inventory, existing-row status, and recovery plan remain unverified. Never run production `db reset`. |
| Security and capture | BLOCKED | No security-advisor or live `service_state` query run. Zero findings, `capture_open=false`, and anonymous-sign-in settings are not verified. No settings changed. |
| Edge Functions | BLOCKED | No function deployed. Pending JWT-on `prior-attach`, JWT-off `gsip-public`, protocol 200, resolution-9 rejection 400, and MCP four-tool smoke checks. |
| Repository variables | BLOCKED | Names observed: `VITE_SUPABASE_PUBLISHABLE_KEY`, `VITE_SUPABASE_URL`. Required `SUPABASE_URL`, `VITE_GSIP_PUBLIC_API`, and `VITE_PRIOR_TILES_BASE` absent. No values printed or changed; legacy URL not deleted. |
| Secret stores | JUSTIN_ACTION | Repository secret-name list and `github-pages` environment secret-name list both empty. `SUPABASE_SERVICE_ROLE_KEY` and `HF_TOKEN` are not present in those GitHub stores. Supabase secret-store contents were not inspected. Credentials must be added through authorized stores/login, not chat. |
| Contributor-rights worker | BLOCKED | Source, target, deployment prerequisites and approval pending. No worker run. |
| Photo QA | BLOCKED | Existing `Private photo QA` workflow is `disabled_manually`. No dispatch or enablement performed. |
| Export | JUSTIN_ACTION | Existing nightly export workflow is `disabled_manually`; dataset approval and token pending. No dispatch performed. |
| Tiles | BLOCKED | Reviewed builder unavailable. `uv run python -m pipeline.build_prior_tiles --max-zoom 8` not run. Publication requires Justin's host approval and deployment go. |
| Pages | BLOCKED | No deployment or build performed. Future build must use `VITE_CAPTURE_LIVE=false`; prerendered pages and `llms.txt` remain unverified. |
| Required CI check | JUSTIN_ACTION | Effective main rules include one approval and review-thread resolution, but no required-status-check rule. Justin must require `validate` once the check exists. Rules were not changed. |
| DNS | JUSTIN_ACTION | WP-SITE-1D cutover remains Justin's action. |
| Legal URLs | JUSTIN_ACTION | Counsel approval of `docs/legal/` and approved URL variables pending. No legal approval inferred. |
| CAPTCHA and paid tier | JUSTIN_ACTION | No provider selected or subscription changed. |
| Opening capture | JUSTIN_ACTION | Explicitly outside this agent's authority; launch gates and Justin's action required. |

Environment checks ran: Docker server `29.8.2` is reachable after sandbox
escalation; Xcode `27.0 (27A266a)` and the iOS simulator SDK `27.0` are installed;
Java is OpenJDK `21.0.1`; Android SDK platforms 29, 33, 34 and 36 and several
`aapt2` build-tool versions are present. Android tools are not on PATH.
`supabase`, `deno`, `gdalinfo`, `psql`, and `pg_prove` are not on PATH. PostgreSQL
with PostGIS/pgTAP and the actual Python GDAL test runtime are not verified.
Having Docker or SDK files does not prove the requested test suites pass.

## Phase 3

All follow-ups are queued until Phase 1 is done, as requested. No follow-up
implementation or speculative source changes were made against the older checkout.

| Follow-up | Next gate |
| --- | --- |
| Cross-tab sync lock | Inspect reviewed queue implementation; restate invariants; add Web Locks fallback and regression tests in its own WP PR. |
| Notifications | SPEC/BUILD_ORDER amendment first; then local-notification implementation and Android dependency checks. |
| Context-photo privacy screening | SPEC comparison of open detectors and their licences first; Justin chooses policy before implementation. |
| Root coding-agent `AGENTS.md` | Collect v3 contribution/deployment commands and link API-consumer `docs/AGENTS.md`, in its own WP PR. |
| App versions from CI | Inspect generated native projects and implement independently of signing/store credentials. |
| Optional manual deploy workflow | Proposal only; amend BUILD_ORDER first; protected production environment and exact-command go gate. |

## Decisions asked once, batched

These recommendations are proposals, not approvals or executed changes. An
unanswered decision remains pending; elapsed time does not authorize anything.

| Decision | Options | Recommendation |
| --- | --- | --- |
| Handoff location | Provide the unzipped directory's absolute path; or make the exact reviewed archive locally available and identify its path. | Supply the original reviewed handoff; do not reconstruct its commits. |
| Production project | Verify/reuse `toxldjgwkxtneoqsazym`; or name another project. | Verify and reuse the existing named `gsip` project if Justin selects it. |
| Tier | Defer upgrade; or explicitly approve a paid tier. | Defer spending while capture is closed. |
| Hugging Face | `global-soil-intelligence/gsip`; or another owner/dataset. | Existing placeholder only if Justin controls and approves that destination. |
| Tiles | Repository-owned GitHub Pages assets; or another approved host. | Pages assets subject to size and privacy review. No host approval inferred. |
| CAPTCHA | Defer; approve Turnstile; or approve hCaptcha. | Defer while capture is closed; either provider needs explicit closed-service approval. |
| Capture / anonymous sign-in | Keep disabled; or revisit after launch gates. | Keep disabled. This agent never opens capture. |
| Apple/Google accounts and signing | Defer; or identify available owner-controlled accounts. | Defer until accounts and signing authority are supplied; never send credentials in chat. |
| Phone backups | Exclude private app data; or approve retention with a documented policy. | Exclude private app storage, subject to Justin's decision. |
| Context-photo screening | Withhold flagged photos for human review; blur; or review-only. | Withhold flagged photos pending review; policy must be decided before implementation. |
| New paid/closed services | None; or explicitly name and approve an exception. | No new service. |
| Licences | Retain MIT / ODbL 1.0 / CC BY-SA 4.0; any change requires a new explicit instruction. | Retain all current licences. |
| Merges | Justin reviews and merges each PR. | Preserve the human merge boundary; no agent approval or auto-merge. |

## Assumptions

- The seven supplied short heads are authoritative pending bundle verification.
- The older local edits are unrelated to the reviewed stack and must be preserved.
- Main's v2.2 documents cannot substitute for the missing v3 documents.
- A project name, prior deployment target, installed SDK, or historical test count
  does not establish current production qualification or passing reviewed-head checks.
- Missing or unanswered approvals remain pending. Production deployment cannot
  advance around the missing handoff or phase-order gates.

Sanitized machine-readable observations are in `evidence.json`. File hashes are
in `SHA256SUMS`. Neither file contains secret values or contributor coordinates.
