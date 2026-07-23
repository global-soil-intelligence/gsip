# Gate C: nine reviewed database migrations

**Prepared locally; not authorized or executed.** Target: `toxldjgwkxtneoqsazym` (`gsip`, `us-east-1`, production `main`). Source is clean `f9e1ac2f8a88671f99b959e476499392297bd30f`; CLI 2.118.0. This is the database portion of `docs/PHASE1_DEPLOYMENT.md`, not authority for any later deployment or capture opening.

## Exact proposed commands

The dry run is preparation; the push must wait for Justin's separate Gate C go after the exact target/command/files are shown. Neither command was run by this preparer.

```sh
GSIP_REPO="/Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/repo"
GSIP_CLI="$GSIP_REPO/node_modules/.bin/supabase"
"$GSIP_CLI" db push --project-ref toxldjgwkxtneoqsazym --workdir "$GSIP_REPO" --skip-vault --dry-run
```

After the explicit Gate C go only:

```sh
"$GSIP_CLI" db push --project-ref toxldjgwkxtneoqsazym --workdir "$GSIP_REPO" --skip-vault
```

## Ordered files and effects

### 20261010120000_wp6b_capture_gate.sql

SHA-256: `d5dc5bb281927e0c3e6d72705ec1d24094de93be17ffa7e02c02c56c375e5964`.

- Creates one RLS-protected service_state row with capture_open=false and a fail-closed capture_is_open helper.
- Replaces grant/submission/photo insert policies to require the capture gate. Only service_role can update the switch.

Existing-data effect: No legacy observation removal; adds one operational switch row.

### 20261010120100_wp6b_path_binding.sql

SHA-256: `7d6d410f6cfb532d9166088e02bea4f36f6e5c02307d674bac3516b76928c017`.

- Adds the owner/submission/shot/UUID photo-path binding trigger for every writing role, including service_role.
- Tightens private incoming Storage insert/update path rules; inserts require capture open and the caller's submission.

Existing-data effect: Existing paths are not rewritten or validated in place; future relevant writes are bound. Existing worker code independently re-derives paths.

### 20261010120200_wp6b_finalize_and_settle.sql

SHA-256: `da54235f99d2935601753d8461393838672cb0c62a9709616d06e1ca83e725fc`.

- Adds submissions.finalized_at and photos.qa_status, owner-only idempotent A/B finalization and service-only settlement.
- Backfills complete legacy A/B sets, derives photo verdicts from completed/dead-letter QA jobs and re-settles legacy submission statuses under the new A/B rules; optional C does not determine status.

Existing-data effect: Existing status, finalization time and per-photo verdict fields may change intentionally; row counts must remain stable. Incomplete sets can return to pending; do not promise status-byte equality.

### 20261010120300_wp6b_k_anonymous_cells.sql

SHA-256: `29e4b3b97b7bbb64e6dbd986d857c73e416a4a7ca4244d4b166210594fc73f3e`.

- Adds resolution and distinct-contributor counts to public cells, requiring resolutions 4/6/8, matching index resolution, at least 3 contributors and consistent counts.
- Replaces service-only atomic public-cell refresh with validation. Deletes legacy cells whose contributor count is unproven before enforcing non-null constraints.

Existing-data effect: Intentional removal of unproven public aggregates; accepted baseline is already 0 cells, so expected post-migration count is 0. No export/rebuild is authorized by this gate.

### 20261010120400_wp6b_attribution_and_metadata.sql

SHA-256: `fe4bf14607abd0ce669e34b849a5b6ee016307bcbfe3e272e429626a55d16561`.

- Adds a NOT VALID safe-attribution constraint, enforced for new writes while preserving existing immutable grants.
- Extends the private camera-metadata allowlist with a bounded colour-space class, and defaults future QA events to deterministic-v2.

Existing-data effect: Existing grant names are not rewritten/revalidated; private metadata remains private. Constraint installation still validates the camera-metadata contract.

### 20261010130000_wp6c_priors.sql

SHA-256: `6f3bdc4b13dbe661eee30e6bd1f74fbe4e6853e200705b07e7ab69f347d3f68b`.

- Adds terminal empty_sources metadata, a service-only resolution-9 prior cache and three service-only upstream token buckets.
- Replaces old claim_prior_job_attempt with service-only atomic claim/token-spend begin_prior_attempt and bounded failure/stale-job helpers.

Existing-data effect: Adds an empty array to each legacy prior job and three bucket rows; no upstream lookup, queue drain or cache population is run by the migration. The old claim RPC is removed, so a stale Edge deployment/drain must not be invoked until its separately gated redeploy.

### 20261010140000_wp6d_contributor_rights.sql

SHA-256: `9cb7c770f3772c463bfa1191741164122513155ab4f60e5db5899fa9c4407790`.

- Creates private deletion_requests, append-only grant_withdrawals, private attribution_reviews and a service-only security-invoker review queue.
- Adds immediate grant-withdrawal/request guards, deleted-user recreation guards, anti-update/delete/truncate protections and service-only idempotent rights/orphan-listing RPCs.

Existing-data effect: Creates mechanisms but files no requests and invokes no worker/deletion RPC; no contribution, object or auth user is deleted by applying this file.

### 20261010150000_wp6e_provenance.sql

SHA-256: `d3e772403dd912fe5146210be802906a8d9be1f5c65516a0d5bbd13c63105f05`.

- Creates one immutable human actor per existing contributor; actor status is revoked only when contributors.auth_uid IS NULL. Missing auth.users alone is not this backfill condition. Adds final revocation and operator guards.
- Backfills every submission with its contributor's actor and server-derived tier: -1 for is_synthetic=true, otherwise 0. Legacy claims default web/unknown/unknown/null; synthetic rows cannot return to field data.
- Adds private allowlisted capture evidence and per-photo tiers, initially null evidence and -1/0 from the parent synthetic flag; future tier 1 depends on corroboration, with tiers 2/3 reserved.
- Creates the published July-v1 terms version and retired records for other existing grant versions, adds the terms FK and received_at=null for legacy grants; new grants require current published terms and a recent nonfuture acceptance.
- Adds server-only gold-label holdout=false and narrows owner selection to exclude the holdout field.

Existing-data effect: Adds 5 human actors if current contributor count remains 5; updates actor/tier columns without deleting rows, fabricating evidence or reclassifying the is_synthetic flag. Legacy received_at remains unknown. Terms row count depends on distinct existing versions, so measure it rather than assume it.

### 20261011090000_wp_agent1_releases.sql

SHA-256: `b61dd6ebbff44b8034585673b01958d4ce45e79e77a30c33245bd89bcf49c5fd`.

- Creates RLS-protected public-read/service-insert dataset_releases with append-only grants and a unique version/revision key.
- Revokes anon/authenticated execution of private mutation-rejection trigger functions; agent interfaces retain only permitted public information.

Existing-data effect: Creates an empty release ledger; does not upload a dataset, export photos or deploy gsip-public.

## Safeguards before the go

1. Gate A completed and passed the saved full readback: exactly 17 reviewed July identities, all 52 counts and cumulative baseline catalog/supplement preserved, advisor zero findings; its --skip-vault dry run verified these exact nine pending files. Bind the completion receipt and recheck if the state changes.
2. Gate B completed under its separate authorization: wavefunction-api absent, and prior-attach version 3/JWT-on selected metadata unchanged. Saved A/B completion evidence does not approve Gate C or redeploy the remaining function.
3. Show this exact command, target and nine hashes; wait for Justin's explicit Gate C go. A/B approvals, signup closure, CI, a merge or this artifact do not approve C.
4. Immediately before execution, verify clean f9 source, CLI 2.118.0, the exact 17 ledger set and a --skip-vault dry run listing only these nine files. Stop on any drift or extra file.
5. Confirm no overlapping migration/auth/operator writer, active QA/rights/export/prior drain or stale prior-attach invocation. If operational suspension is needed, present it separately for authority; this plan changes no schedule or service.
6. The required row-bearing migration test already passed 13/13 at f9 on 2026-10-12, and the isolated cumulative rehearsal passed 64/64. Repeat if source, target schema or accepted assumptions change; do not substitute an empty successful run.
7. Keep the recoverable original ledger backup private and durable. It is not a rollback of application DDL/backfill. Stop on a failed/partial push, record the per-file ledger and propose a reviewed fix forward; no automatic retry/reset/rollback.
8. Do not use --include-all, --include-seed, --include-roles, db reset or new SQL. Keep --skip-vault to avoid unrelated Vault changes; do not weaken RLS or reapply the July baseline.

## Post-migration readbacks

- **Ledger exact set:** 26 identities = the unchanged 17 reviewed July files plus these exact 9 October files; foreign identity absent; no missing/duplicate/unknown name. Count alone is insufficient.
- **Supabase security advisor:** Zero findings on fresh production readback. Any finding is reported and stops further steps; no automatic weakening or generic suppression.
- **Capture gate:** Exactly one service_state row and capture_open=false; capture_is_open reads false. Do not update capture, enable anonymous auth or publish a capture-live Pages artifact.
- **Auth configuration:** Fresh persisted target-bound dashboard readback: Allow new users to sign up=false and Allow anonymous sign-ins=false; email confirmation stays enabled. The existing signup-closure receipt proves configuration at its recorded time, not an executed signup smoke test.
- **Counts:** All original table counts stay equal to the accepted baseline apart from the intended migration ledger 17 to 26; existing h3_cells remains 0. Managed realtime.schema_migrations=89 is the accepted owner baseline, not an unexplained override. Unexpected platform drift requires a new explicit reconciliation decision.
- **New tables:** service_state=1; upstream_buckets=3; prior_cell_cache=0; deletion_requests=0; grant_withdrawals=0; attribution_reviews=0; actors=5; terms_versions=one published July-v1 plus one retired row per other distinct existing grant version, computed from aggregate preflight; dataset_releases=0.
- **Legacy settlement/QA:** Aggregate A/B-complete count matches finalized_at backfill; photo verdict aggregates follow completed/dead-letter QA jobs; submission status aggregates satisfy the reviewed settlement table. Statuses may change intentionally. No real row contents or per-contributor data in receipts.
- **Actor/provenance backfill:** One human actor per contributor and every submission actor bound to that contributor; no missing/duplicate/foreign actor. Actor revoked iff existing auth_uid is null for this backfill. Submission and photo tiers are exactly -1 when parent is_synthetic is true and otherwise 0; no tier 1+ is invented. Synthetic flag aggregate is unchanged; legacy claims web/unknown/unknown/null and all legacy photo evidence null.
- **Terms/holdout:** Every legacy grant resolves to a terms row; only July-v1 active and all other legacy versions retired. Every legacy received_at stays null. Existing gold labels default holdout=false, with field inaccessible to authenticated owner selection. Do not print legacy term strings or grant names.
- **RLS and privileges:** Read sanitized catalog/supplement metadata and compare to the reviewed 26-file reference, preserving only the already reviewed exact five surviving ownership aliases and hosted extension/schema-grant metadata. All 20 public base tables have RLS, exact role/column privileges, owners, private function grants and grantability; server-only tables remain inaccessible to public/client roles. Do not execute a write smoke test in production.
- **k-anonymity:** Zero public-cell constraint violations: only resolution 4/6/8, matching index/resolution, n_contributors>=3 and n_submissions>=n_contributors. Empty table is expected; no export or public refresh is performed here.
- **Gate B inventory retained:** Foreign function still absent and intended Edge Functions unchanged by a database-only operation. Edge redeploy and protocol/MCP smoke tests are later separate gates.

Existing public/application count baseline (counts only):

| Table | Expected rows |
| --- | ---: |
| `auth.users` | 0 |
| `public.contribution_grants` | 5 |
| `public.contributors` | 5 |
| `public.gold_labels` | 0 |
| `public.h3_cells` | 0 |
| `public.photos` | 25 |
| `public.predictions` | 0 |
| `public.prior_jobs` | 25 |
| `public.priors` | 0 |
| `public.qa_events` | 0 |
| `public.qa_jobs` | 25 |
| `public.submissions` | 25 |
| `realtime.schema_migrations` | 89 |
| `storage.buckets` | 2 |
| `storage.objects` | 0 |

The JSON companion binds every original counted table, not just this compact table.

## Authority and known transition limits

- The nine files contain no WP-6f photo screening, privacy-screen status, detector, or runtime data-only export mode. The owner-requested #38 gate requires no new photo publication until WP-6f is deployed and calibration is approved; eligible releases before then must be structured data only.
- The bound f9 export can include photos. Do not dispatch/publish that photo path under this gate. A reliable data-only export change or WP-6f implementation needs its own reviewed work package and applicable specification approval; do not patch migration architecture or assume individual attribution review satisfies the photo gate.
- No worker dispatch, Edge Function redeploy, repository-variable change, secret read, Hugging Face publication, tile upload, Pages deployment, signup/capture opening or store action is covered by C. Follow PHASE1_DEPLOYMENT section by section with separate exact-target go where required.
- CLI database push can partially apply the ordered chain; the original ledger backup does not undo new status/tier backfills. Preserve receipts and stop on failure, with no production reset or automatic replay.
- Counts are necessary but not proof of unchanged field values or seed classification. Justin's seed classification is owner evidence; the migration obeys the actual is_synthetic flags and must not silently recategorize them.
- Local reference/rehearsal uses platform stand-ins, and prior success is not proof of production success. Post-migration hosted readbacks remain required.

## Evidence bindings

- `production-gates-a-b-execution-receipt-2026-10-12.json`: SHA-256 `c4934bed71dc8427648e89668f2899eedfc033ab9a0d9371d760a5440333f0a4`. Saved A/B completion at 2026-10-12T12:48:31.792598+00:00; C remains unapproved.
- `gate-a-03-final-ledger-2026-10-12.json`: SHA-256 `0fc203968deff91e10f2e8a0999104485038cf3f0619767bc077b873cf901367`.
- `production-accepted-count-baseline-2026-10-12.json`: SHA-256 `6156534e84c43055c6764f76276b34b1557474614958b5944e4969e6e94f20eb`.
- `production-signup-closure-action-readback-2026-10-12.json`: SHA-256 `bfec01a0ac075bffaf33f9d143a36f9481638a24ace17d59d9a4e5a0c1fc2554`.
- `gateab-migration-test-2026-10-12.json`: SHA-256 `d336e4e84164b60418cb8465cf2c654579638ceddca7b4d60972e65c026636a8`.
- `gateab-rehearsal-2026-10-12.json`: SHA-256 `c0736221cbf9ffaba5a60602df1f532a0768fab7c14230480a38c465760eb94f`.
- `canonical-ledger-reconciliation-rehearsal.json`: SHA-256 `4080346f1d0935d3bc93a428df227eaf7380450f03be7c2e1e1dcd6591372cef`.
- `canonical-catalog-target26.json`: SHA-256 `eca562018a82a5df9f2ddd37b1f47e81a26be709f34e4b967c21d5442a562393`.
- `canonical-catalog-target26-supplement.json`: SHA-256 `1ea270359d6b9587d1dc444e9196cc4628c49d21047fa4d0604cfc0925ea136d`.

This artifact contains only public migration summaries, metadata hashes, aggregate counts and prepared command text. No credentials, raw images, row contents, precise points or foreign source are included.
