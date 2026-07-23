Implement private photo-screening authority before any photograph can enter a public release. Existing QA passes confer no privacy clearance. Every legacy/new photo starts pending with an unknown digest; eligible structured data remains separately governed. This is source preparation only: no production migration, worker activation, reviewer provisioning, model selection or publication.

## Work package and invariants

WP-6fA, stacked on spec v8 (#52). Preserve I1–I15 and B1–B8, particularly I7 private coordinates/uploads/metadata, I12 public-agent anonymous authority, licence invariants and all launch gates. Capture, policy, deployment-ready and independent photo-publication gates remain closed. Existing QA/settlement, public photo columns/client grants and rights worker signatures/bodies remain unchanged.

Add eight restrictive private tables and nine dependency-bound service-only invoker RPCs. Admin-only policy selection, owner approval, deployment readiness and operator provisioning are not callable by workers. Exact content/policy revisions and leases prevent stale completion. Server-derived personal operators, immutable review UUIDs and permanent human withholding preserve private review authority. Contributor-first erasure removes private payload and retains only minimal opaque refusal identities.

## Acceptance and verification

- [x] Private restrictive RLS and exact bounded RPC envelopes; direct private client/service table access denied.
- [x] Default-closed gates and immutable content/policy/audit bindings; legacy/new A/B/C photos pending.
- [x] Contributor-first rights cleanup, stale/replayed request refusal and honest unchanged old-worker completion.
- [ ] Corrected independent review and exact-head CI evidence appended when available.
- [ ] Full-history secrets check: held on the single inherited noncredential browser-harness fingerprint awaiting Justin's explicit exception. No new suppression or scanner change.

Original frozen local evidence: 143 new privacy assertions; 593/593 isolated standard-fixture assertions; 45 populated migration assertions; six library and 21 photo genuine two-connection cases. Corrected frozen SQL SHA25652ea34b5b20be0ccec307fdcab0d865f1b8f8a8826f420b26d7332d95630a9c9: author593/593 isolated and143/143privacy; root45/45migration + six library/31photo genuine races. Root lint, TypeScript typecheck, race-runner Ruff/mypy, shell/format and pinned authored-file gitleaks8.21.2 passed. Independent final closure is pending. Root also ran the populated rehearsal before applying only the original additive migration to local Supabase Docker. Root subsequently compiled only the corrected function/trigger definitions locally without a ledger/count/gate change: local ledger30, five contributors/25submissions/50photos/zero auth users; capture, photo publication/deployment and selected policy remain false/unset. Actual local-platform db:test ran 593 assertions, failed three existing positive-ingest RLS assertions (25/29/33) in a closed local-seed context, and passed all 143 new privacy assertions; that platform run is not claimed green. Actual complete CI with its normal disposable fixture remains required.

## Changes after review

- Replaced ambiguous joined source locking with explicit contributor-first parent/photo SHARE NOWAIT admission and per-source exception cleanup. A mid-lock direct source deletion previously deadlocked; contention now conservatively refuses/skips authorization and releases partial locks.
- Added early contributor-first photo insertion admission and a refreshed withdrawal check before downstream FK/content creation. A waiting optional-photo insert previously recreated private state after withdrawal/account deletion.
- Refuse non-READ-COMMITTED execution rather than allowing stale stronger-isolation snapshots to resurrect rights. Preserve the existing public withdrawn-photo error text and every old RLS/permissions check.

## Assumptions and remaining gates

- Hosted PostgREST/default worker execution uses READ COMMITTED. Stronger transaction isolation is refused conservatively by the new authority/admission path.
- Existing sanitized Storage objects are privately held; registering a digest/count is a trusted-service assertion, not a SQL download or detector verdict.
- Publication requires all WP-6f packages deployed plus separately owner-approved calibration/policy and reviewer provisioning; this PR creates no operator or model approval.
- Transaction checks cannot make a later filesystem/Hub operation atomic with withdrawal. Takedown/purge obligations remain.
- All fixtures are synthetic; new geometries are EMPTY. No contributor data, tokens or credentials enter code, logs or PR text. No dependency or licence change.
- Host PostgreSQL/GDAL/Deno/Android SDK/Xcode availability is limited; Docker PostgreSQL/PostGIS/pgTAP was actually used, and CI supplies the remaining checks. Simulator builds do not establish physical-device backup compliance.

Codex authored the implementation and fixes for Justin Hart, human of record. Independent source review is separate from a GitHub approving review. No agent certifies Justin's DCO, bypasses protections, deploys or opens capture.
