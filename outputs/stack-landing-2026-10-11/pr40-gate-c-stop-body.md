## Problem and result

Production's July GSIP migrations use thirteen timestamps different from the reviewed files, and an owner-confirmed accidental Wavefunction deployment left one history record and an Edge Function. This package prepares the exact gated reconciliation without changing production: a strict offline catalog comparator, an evidence-based authority assessment, the thirteen timestamp pairs, recoverable private backup requirements, and separate history/function/migration approval gates.

## Invariants

Application rows, effective schema, RLS, grants and GSIP functions remain unchanged during history repair. Capture stays closed and production anonymous sign-in remains disabled by owner policy; the absent service_state and live auth settings need later readback. Four unchanged July identities survive, none of the nine October migrations is marked applied, no foreign application source is imported, and no production reset/DDL replay is proposed. I5/I7/I12 and existing licence/service guardrails remain intact; receipts contain aggregate counts and schema metadata only.

## Evidence and validation

- Independent aggregate readback: 5 contributors, 25 submissions, 25 photos, 0 auth users, 0 public cells; foreign tables absent. Security advisor has zero findings at readback.
- All seventeen canonical July migrations were reconstructed without production data/credentials. Actual production columns, constraints, indexes, triggers, table/function owners, function definition hashes and grantability, public/private grants and Storage policies match, apart from six exact bound ownership aliases and six preserved platform metadata additions. The document shows which effective baseline is authoritative for wp1_schema, wp1_rls and wp4b_photo_qa; it does not claim historical text/data-effect equality.
- **51 meaningful synthetic comparator tests pass**, including changed RLS/owners/privilege delegation, malformed or duplicate evidence, and any expanded exception. Initial absent-module test failed; new owner/grantability tests failed against the earlier comparator before the fields were added.
- Offline comparison of refreshed actual extracts passes with exactly 12 documented differences and zero unexpected differences. Errors print hashes and fixed labels, never arbitrary input values. The helper has no network, subprocess or SQL execution.
- Isolated PostgreSQL17.6/PostGIS rehearsal: **64/64 assertions pass**, modeled ledger18→31→18→17→26, application/catalog/sentinel preservation, ownership/alias negative controls, nine pending upgrades and closed capture. Auth/Storage are repository stand-ins; this models documented ledger operations rather than running Supabase CLI repair. Coordinate-free synthetic inputs only.
- Full local Python suite **271 passed, 4 GDAL-dependent tests skipped**; full Ruff and mypy37files pass; language and formatting pass. Required unchanged migration suite ran **13/13** on the same reviewed SQL chain. Local GDAL/Deno/full hosted-Supabase verification relies on CI. CI for this new head is pending.
- Independent peer review caught and corrected the owner/grantability proof gap before commit. No detection rule, scanner suppression, permission/dependency check or RLS protection was weakened.

## Assumptions

- Justin's production target, accidental foreign deployment attribution and seed classification are owner statements; independent checks establish counts/schema, not seed-row provenance or all historical DML effects.
- Source f9e1ac2 is the reviewed migration chain; this branch changes none of its SQL files. Fresh evidence/source identity must still agree before execution; any concurrent writer or drift stops the plan.
- Private durable ledger backup and isolated restore of all original names/statements are prerequisites, not yet completed. Digests alone cannot restore the original ledger.
- Platform extensions and grants are preserved. Stand-in testing does not prove the entire hosted platform identical.
- CLI2.118.0 flags and repair behavior were verified; another version requires a new exact command review. The three repair invocations are not one atomic transaction.
- This PR or its merge grants no production go. History repair, deletion of only wavefunction-api, and the nine new migrations each need Justin's explicit authorization. Main's existing automatic Pages deployment needs a protected approval gate before merges.

## Dependencies and licensing

No new dependency, paid/closed service, architecture or licence change. MIT code, ODbL1.0 data and CC BY-SA4.0 photos remain unchanged.


## Changes after review

- cf063aa records the completed private history recovery proof:18/18 names/versions, complete statement arrays and all six metadata fields match fresh production hashes after an isolated network-disabled restore; one ledger table/zero user functions, no foreign SQL execution. Private SQL files stay outside Git with owner-only permissions. Secret scan8.21.2 found zero matches with no custom suppression.
- Replaced usage-only --help wording with the actual four-input offline comparison command and explicitly scoped capture_open=false to the local post-upgrade reference. The three exact production history-repair commands, target, and separate approval gates remain unchanged.
- Initial head860fe9e passed validate and both gitleaks checks; current documentation headcf063aa CI is pending. No history repair, production migration, function deletion or deployment has run.


### Current-head CI evidence

- Forward documentation head `cf063aa5865a86eb86250e3a1f8287545e51f037`: [validate run 38195739800](https://github.com/global-soil-intelligence/gsip/actions/runs/38195739800) and both full-history secret scans succeed. Same-repository DCO check is skipped by existing policy. No production history repair, function deletion, new migration or deployment has run; Gates A/B remain pending.


### Fresh read-only production evidence

- No drift: all 52 aggregate table counts, eighteen full ledger-row hashes and both schema catalogs match the bound preapproval receipts. Security advisor returns zero findings. Private backup hashes remain unchanged.
- Anonymous sign-in is now independently verified disabled on the exact GSIP project Auth providers page (switch value 0; Save changes disabled). No setting was changed. This supersedes the earlier unverified state recorded when the source plan was prepared; live service_state still does not exist.
- No production history repair, function deletion, new migration or deployment has run. Separate Gate A/B approvals remain pending.


### Changes after review — authorized Gates A/B execution (2026-10-12)

Executed the unchanged Gate A commands on production `gsip` (`toxldjgwkxtneoqsazym`, us-east-1) after Justin explicitly accepted the refreshed platform Realtime ledger baseline of 89. Independently verified the exact full ledger set and surviving whole-row hashes after each repair: **18 → 31 → 18 → 17**. Final dry run exits 0 and its plan lists **only the nine October migration files**. Application counts/catalogs/RLS and the private recovery backup are unchanged; the security advisor reports zero findings. Fresh required migration test passed 13/13 and the disposable rehearsal passed 64/64 before execution.

Gate B then deleted **only `wavefunction-api`**, with exit 0. Inventory readback shows only `prior-attach`, active at version 3 with JWT verification on; all selected metadata equals the pre-delete readback. `gsip-public` remains absent.

Under a separate explicit Auth-only go, new-user sign-up was disabled and verified after save/reload; anonymous sign-in remains off, Email provider and Confirm email unchanged. No October migration, GSIP function deployment, worker, export, tile publication or Pages deployment has run. Gate C was presented and awaits a separate go. The live `service_state` table is still absent, so live `capture_open = false` cannot yet be claimed.

Execution receipt SHA-256: `c4934bed71dc8427648e89668f2899eedfc033ab9a0d9371d760a5440333f0a4`. Post-A schema/count/security receipt SHA-256: `77a91551ad9e04f11ade62478a23149c9dec74bbb8d7fb5f424655c7fc86f4bb`. Signup action/readback receipt SHA-256: `bfec01a0ac075bffaf33f9d143a36f9481638a24ace17d59d9a4e5a0c1fc2554`. All receipts contain metadata or aggregate counts only.

Assumptions/limits: platform-ledger drift cause remains unknown and was accepted by the owner as a new baseline; seed classification is owner-supplied. The first local dry-run extractor counted both renderings of the same filenames; its diagnostic receipt was preserved and the exact nine-entry CLI bullet plan independently verified before Gate B. No new suppression, dependency, licence, source change or architecture change was made. The photo-publication policy in #38 still needs implementation; photo-capable publication remains held.


### Changes after review — Gate C execution and security stop (2026-10-12)

Justin explicitly authorized only the nine October migrations. The exact reviewed `db push --skip-vault` ran once on `gsip` (`toxldjgwkxtneoqsazym`, us-east-1), applying all nine with exit 0. Exact ledger identity set is 26; original 17 full history-row hashes remain unchanged. All 61 table counts match; original application counts remain 5 contributors, 25 submissions, 25 photos, zero auth users and zero public cells. Effective target26 schema/RLS/privileges match the reviewed reference with only the five bound policy aliases and known hosted metadata allowances. Capture is now independently verified false. Sign-up and anonymous sign-in remain disabled. All sixteen independent backfill anomaly counts are zero.

**STOP: 16/17 postchecks pass; the zero-security-findings gate fails.** Advisor reports seven finding instances on six objects across three categories: INFO RLS/no-policy for attribution_reviews and grant_withdrawals; WARN anonymous executable SECURITY DEFINER for capture_is_open(); WARN authenticated executable SECURITY DEFINER for capture_is_open(), current_auth_user_exists(), finalize_submission(uuid) and my_submission_accepts_uploads(text). These definitions match the reviewed catalog; no policy/grant was weakened to clear the advisor. No finding was suppressed, no additional SQL ran, and no Edge deployment/worker/publication followed. A local-only remediation proposal is being prepared; any privilege architecture change requires a specification update first and any further production migration requires a separate exact-command go.

Full hosted postcheck receipt SHA-256: `85b1f1b89960582446550883ea3556a34d2a3efba9b7a414d9023d7cc246c73e`. Execution/stop receipt SHA-256: `6070c7fac31931203f85625b80e81b37d4d703c518eac0822741dfcaf708966d`.

The separately requested Pages environment task is complete: Justin remains the sole required reviewer, administrator bypass is disabled and persisted, all other protections and main/gh-pages policies preserved. No merge or Pages deployment. Receipt SHA-256: `3b5df1ba9ce8918d53fe35f09df147a4d046c8efbe0b2619b5821018303aca9e`.

Assumptions/limits: counts do not prove unchanged column values; reviewed finalization/QA/provenance backfills intentionally change fields, with aggregate predicates independently checked. Security findings flag intended guarded helpers/RPCs and default-deny service-only tables; their existence alone is not proof of a data leak, but the zero-findings requirement is unsatisfied. No automatic retry/reset/rollback or broadened authorization.
