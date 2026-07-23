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
