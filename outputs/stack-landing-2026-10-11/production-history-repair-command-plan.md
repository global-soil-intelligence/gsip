> Historical preparation note. Superseded by green PR #40 at cf063aa and docs/PRODUCTION_RECONCILIATION.md. See REPORT-current.md for verified backup/restore evidence and pending Gate A/B approvals. No repair or deployment has run.

# Prepared production migration-history command plan

Target: `toxldjgwkxtneoqsazym` (`gsip`, `us-east-1`). **Prepared only; no production go and no mutation executed.** Source: existing count and statement-digest receipts. No SQL bodies, contributor contents or secret values are included. The baseline has rows, so the repository migration test and an exact production-baseline rehearsal are mandatory before approval.

The installed CLI in the reviewed checkout is **2.118.0**; its local help confirms `--project-ref` for `migration repair`, `migration list` and `db push`. The original workspace's separate CLI is 2.109.1 and lacks that repair flag. Use the exact reviewed binary and a pinned reviewed checkout. CLI 2.118.0 `db push` also updates Vault unless `--skip-vault` is supplied; this plan excludes that unrelated mutation. Help evidence: `production-reconciliation-cli-help-2.118.0.json`.

## Invariants and prerequisites

- Keep existing rows, RLS, grants and capture restrictions intact; never reset production or rerun historical DDL to hide ledger drift.
- Match the fresh target/ledger counts and SHA-256 statement metadata to these receipts immediately before mutation. Stop on drift. Counts alone do not prove historical SQL equivalence.
- Resolve the six recorded historical SQL differences (four matching-timestamp entries plus `wp1_performance_indexes` and `wp4b_photo_qa`) through the separately reviewed reconciliation package. These commands do not resolve a schema difference.
- Run `scripts/db-migration-test.sh` and the exact-baseline synthetic rehearsal before approval. Preserve the original history/digest receipt privately and bind the reviewed source commit.
- Post this exact target and final commands, then wait for Justin's explicit **go for history reconciliation**. That go does not authorize the nine new migrations or function deletion.
- Preserve all four unchanged baseline entries. Add only thirteen verified equivalent local identities; remove only their thirteen superseded remote identities and the single separately identified stray Wavefunction history entry. Do not mark any new migration applied.

## Timestamp mapping

| Baseline name | Existing remote version | Reviewed local version | Recorded SQL comparison |
| --- | --- | --- | --- |
| `wp1_v22_privacy_and_grants` | `20260722182403` | `20260722181500` | RAW_EQUAL |
| `wp1_performance_indexes` | `20260722182446` | `20260722183000` | DIFFERENT_UNVERIFIED |
| `wp4_prior_jobs` | `20260722190912` | `20260722190000` | RAW_EQUAL |
| `wp4_prior_jobs_hardening` | `20260722191140` | `20260722190500` | RAW_EQUAL |
| `wp4b_photo_qa` | `20260722191802` | `20260722193000` | DIFFERENT_UNVERIFIED |
| `wp6_export_guardrails` | `20260722194033` | `20260722200000` | RAW_EQUAL |
| `phase1_actor_hardening` | `20260723011122` | `20260723002255` | OUTER_WHITESPACE_EQUAL |
| `qa_event_provenance` | `20260723011144` | `20260723004439` | OUTER_WHITESPACE_EQUAL |
| `public_h3_aggregates` | `20260723011159` | `20260723005752` | OUTER_WHITESPACE_EQUAL |
| `atomic_public_h3_refresh` | `20260723011219` | `20260723010313` | OUTER_WHITESPACE_EQUAL |
| `atomic_prior_attempt_claim` | `20260723050851` | `20260723044745` | OUTER_WHITESPACE_EQUAL |
| `document_authenticated_h3_role` | `20260723050903` | `20260723045317` | OUTER_WHITESPACE_EQUAL |
| `remove_public_submission_residue` | `20260723050918` | `20260723045606` | OUTER_WHITESPACE_EQUAL |

The four unchanged versions are `20260722164727`, `20260722164749`, `20260722164806`, `20260722170020`. The only extra entry is `20260730174047_wavefunction_beta_schema`. Retiring its history record does **not** remove schema objects or deployed functions; no schema drop is included.

## Proposed history commands — run only after explicit go

Run from the approved reviewed checkout. These are command text, not a runnable dispatch artifact. Set the checkout path to that reviewed source before approval; the existing evidence checkout is:

```sh
GSIP_REPO="/Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/repo"
GSIP_CLI="$GSIP_REPO/node_modules/.bin/supabase"
"$GSIP_CLI" --version
"$GSIP_CLI" migration list --project-ref toxldjgwkxtneoqsazym --workdir "$GSIP_REPO"

"$GSIP_CLI" migration repair --project-ref toxldjgwkxtneoqsazym --workdir "$GSIP_REPO" --status applied 20260722181500 20260722183000 20260722190000 20260722190500 20260722193000 20260722200000 20260723002255 20260723004439 20260723005752 20260723010313 20260723044745 20260723045317 20260723045606
"$GSIP_CLI" migration repair --project-ref toxldjgwkxtneoqsazym --workdir "$GSIP_REPO" --status reverted 20260722182403 20260722182446 20260722190912 20260722191140 20260722191802 20260722194033 20260723011122 20260723011144 20260723011159 20260723011219 20260723050851 20260723050903 20260723050918
"$GSIP_CLI" migration repair --project-ref toxldjgwkxtneoqsazym --workdir "$GSIP_REPO" --status reverted 20260730174047

"$GSIP_CLI" migration list --project-ref toxldjgwkxtneoqsazym --workdir "$GSIP_REPO"
"$GSIP_CLI" db push --project-ref toxldjgwkxtneoqsazym --workdir "$GSIP_REPO" --dry-run --skip-vault
```

Add verified local identities before retiring old ones so an interrupted sequence retains a duplicate/blocked ledger rather than forgetting already-applied baseline entries. Each CLI invocation is a separate operation; the whole sequence is not atomic. Stop immediately on any failed command or unexpected readback; do not run `db push` between repairs. Expected counts: original 18 → 31 after adding thirteen → 18 after retiring thirteen → 17 after removing the stray entry. Confirm exact identities and application row counts, not only totals. The final dry run must list exactly the nine pending migrations below, and no historical baseline SQL.

## Separate function deletion go

After Justin separately authorizes deletion of this one stray deployed function:

```sh
"$GSIP_CLI" functions delete wavefunction-api --project-ref toxldjgwkxtneoqsazym --workdir "$GSIP_REPO"
```

Verify the deployed-function inventory contains every intended GSIP function and no `wavefunction-api`. No other function deletion, deployment or restoration is included.

## Nine additions remain pending

- `20261010120000_wp6b_capture_gate.sql`
- `20261010120100_wp6b_path_binding.sql`
- `20261010120200_wp6b_finalize_and_settle.sql`
- `20261010120300_wp6b_k_anonymous_cells.sql`
- `20261010120400_wp6b_attribution_and_metadata.sql`
- `20261010130000_wp6c_priors.sql`
- `20261010140000_wp6d_contributor_rights.sql`
- `20261010150000_wp6e_provenance.sql`
- `20261011090000_wp_agent1_releases.sql`

After reconciliation is verified, post a separate nine-migration plan and exact `db push` command for Justin's migration go. Do not use `--include-all`, `--include-seed`, `--include-roles`, repair with an empty version list, or production `db reset`. This plan contains no secret/password/connection-URL arguments.

Supabase documents migration repair as insertion/deletion of history records, rather than SQL execution: [official CLI reference](https://supabase.com/docs/reference/cli/supabase-migration-repair). Actual flags above were verified against installed2.118.0 because the online reference can lag installed releases.

Assumptions: target selection remains Justin's; existing count/hash receipts are immutable observation evidence, not current-state proof; the approved reconciliation source will demonstrate equivalent effective baseline schema and any historical data effects before ledger repair; no intervening database writer/CLI history repair is active; the thirteen mappings preserve baseline order; original reviewed commits remain intact.
