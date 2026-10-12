# Production reconciliation (WP-OPS-2)

**Prepared, not executed.** Target: `toxldjgwkxtneoqsazym` (`gsip`, `us-east-1`). Justin identified an accidental Wavefunction deployment and requested this separate package before any migration go. No foreign application SQL belongs in GSIP. No production history repair, function deletion, new migration or deployment is authorized by this document or its merge.

## Invariants

Application rows, effective schema, RLS, grants and existing GSIP functions survive history reconciliation unchanged. Capture remains closed; anonymous sign-in remains disabled by owner policy. The baseline does not yet have `service_state`, so its eventual `capture_open = false` must be checked after the separately approved migrations. Production anonymous-auth configuration has not been independently verified. Never reset production, rerun baseline DDL, use `--include-all`, or mark any October migration applied during repair.

Only thirteen superseded July timestamp identities and the single foreign history identity may be retired. Preserve the four unchanged July identities. Keep an owner-private recoverable original ledger; digests alone are not a backup. Stop on drift, a failed command or an unexpected count, rather than continuing a partially completed sequence. All public receipts contain metadata and aggregate counts only; no contributor contents, function bodies, credentials or coordinates.

## Evidence and authority (2026-10-11)

Independent readback found **5 contributors, 25 submissions, 25 photos, 0 auth users, 0 public cells**. All 52 non-system base tables were counted without retrieving their rows. The foreign relations `wf_cards` and `wf_witnesses` are absent across non-system schemas. Security advisor returned an empty findings list; every public base table has RLS enabled. These observations must be repeated before execution.

Production has eighteen ledger entries: seventeen GSIP baseline identities, thirteen using different timestamps, plus `20260730174047_wavefunction_beta_schema`. Justin attributes the foreign deployment to his separate private application and identifies `wavefunction-api` version 2 as a sign-in-required 410 stub. Function inventory independently confirms version 2 with JWT verification enabled; its 410 response has not been independently authenticated. This package proposes deleting that one function after a separate go, and importing none of its source.

The reviewed repository at `f9e1ac2f8a88671f99b959e476499392297bd30f` supplies the authoritative future GSIP migration chain. To establish effective baseline compatibility, all seventeen July files were applied to an isolated PostgreSQL 17.6/PostGIS reference, without production data or credentials. Production's PostgreSQL minor version is also 17.6. The reference uses repository auth/Storage stand-ins; it does not reproduce the complete hosted platform.

| Source with historical differences | Comparison with actual production                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Authority for subsequent changes                                                                 |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `wp1_schema`                       | All 96 column definitions, 62 constraints, 23 indexes and 11 table/RLS states match the cumulative reviewed seventeen-migration baseline exactly. Later July migrations have already converged the effective schema.                                                                                                                                                                                                                                                                                      | Reviewed cumulative baseline; no replay or schema rewrite is needed.                             |
| `wp1_rls`                          | Six ownership predicates use a different relation alias. Every other policy field, table/function owner, public/private function definition hash, function privilege and grantability, table/column grant, trigger and Storage policy matches.                                                                                                                                                                                                                                                            | Preserve current equivalent ownership predicates; do not weaken or rewrite RLS to align text.    |
| `wp4b_photo_qa`                    | Effective photo-QA columns, constraints, grants, triggers and functions match the reviewed cumulative baseline. The recorded historical body matches [repository commit 969076a](https://github.com/global-soil-intelligence/gsip/blob/969076a394aef4af8c65b55a664001b68fc2bfa6/supabase/migrations/20260722193000_wp4b_photo_qa.sql); the current file adds only `IF NOT EXISTS` to `ADD COLUMN gps_accuracy_m` on submissions. The existing column is nullable REAL with a validated nonnegative check. | Reviewed idempotent migration file for future reference; already-applied QA DDL is not replayed. |

The six alias differences are `photos_insert_own` (CHECK), and `photos_select_own`, `gold_labels_select_own`, `predictions_select_own`, `priors_select_own`, `qa_events_select_own` (USING). Their sole expression difference is the bound relation name:

```sql
-- Reviewed reference
submission_id IN (SELECT submissions.id FROM public.submissions
                  WHERE submissions.contributor_id = public.current_contributor_id())
-- Existing production
submission_id IN (SELECT s.id FROM public.submissions s
                  WHERE s.contributor_id = public.current_contributor_id())
```

The comparator accepts only those exact recorded deparsed expressions on those six named policies. It does not strip SQL text or accept arbitrary alias changes. It rejects changed owners, function grantability, roles, operation, permissiveness, expression, grants, missing sections, duplicate objects, missing objects and unknown objects.

The other differences are hosted-platform metadata: additional `pg_stat_statements` 1.11, `supabase_vault` 0.3.1 and `uuid-ossp` 1.1 extensions; `dashboard_user` CREATE/USAGE on `extensions`; and `postgres` USAGE on `public`. All remain intact. No extra public view exists; both private baseline function hashes and all five `storage.objects` policies match. Platform metadata outside this comparison is not silently declared equivalent.

Justin reports fourteen historical bodies differ only in comments/whitespace and three differ substantively. The independent statement-digest readback establishes some exact/outer-whitespace matches, but does not itself prove all fourteen comment-normalized matches. The compatibility conclusion instead rests on the strict, cumulative effective-schema comparison, not a claim that every historical body is byte-identical or that its past data effects can be recovered from schema hashes.

Local evidence lives outside Git under `outputs/stack-landing-2026-10-11/`:

- `catalog-snapshot.sql`: SHA-256 `89028b8da3460182b59ca9a87b57c6fb1e9be32660dc5806995149d0f9a1db0f`.
- `catalog-snapshot-supplement.sql`: SHA-256 `92831e8adcefae9ecd0a1141b833bab1de031d63b385bc7a1c7143ee5d8cd2c9`.
- `canonical-catalog-baseline17.json`: SHA-256 `83b9702c433bbcd0b37382bc85a61767c262f64d0caefeec4902322929b0ffca`.
- `canonical-catalog-baseline17-supplement.json`: SHA-256 `dd8bdda47d262ef2e86e1679d55c45de8cdf706e4b3f394272c88997e9a7fb7d`.
- `production-catalog-before-reconciliation.json`, its supplement, the strict comparison, aggregate counts, source/image receipt and rehearsal outputs bind the observed production state to that reference. They are observation evidence, not authorization or a recovery dump.

Reproduce the comparison from this reconciliation branch without a database connection. Reference and production inputs must be schema-only catalog JSON. The helper never connects to a database or executes a repair command. Fifty-one synthetic unit tests reject changes to the protections the comparison checks.

```sh
GSIP_EVIDENCE="/Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11"
uv run --frozen python -m scripts.reconciliation \
  --reference-catalog "$GSIP_EVIDENCE/canonical-catalog-baseline17.json" \
  --observed-catalog "$GSIP_EVIDENCE/production-catalog-before-reconciliation.json" \
  --reference-supplement "$GSIP_EVIDENCE/canonical-catalog-baseline17-supplement.json" \
  --observed-supplement "$GSIP_EVIDENCE/production-catalog-before-reconciliation-supplement.json"
```

The isolated reconciliation rehearsal passed **64/64 assertions**: baseline ownership/RLS checks with two synthetic identities, the six exact alias forms, a privacy-weakening negative control, ledger transitions 18 → 31 → 18 → 17 → 26, unchanged synthetic application rows/catalog during metadata repair, and all nine October upgrades. Post-upgrade metadata matches the reviewed target apart from five exact surviving ownership aliases. The local post-upgrade reference has `capture_open = false`. This rehearses the documented ledger insert/delete effects in disposable SQL; it does not claim to have executed Supabase CLI repair or any production operation. The driver and coordinate-free SQL inputs are saved alongside `canonical-ledger-reconciliation-rehearsal.json` outside Git. No foreign source was used, and synthetic geometry is empty rather than a coordinate literal.

## Timestamp mapping

| Name                               | Existing remote  | Canonical local  |
| ---------------------------------- | ---------------- | ---------------- |
| `wp1_v22_privacy_and_grants`       | `20260722182403` | `20260722181500` |
| `wp1_performance_indexes`          | `20260722182446` | `20260722183000` |
| `wp4_prior_jobs`                   | `20260722190912` | `20260722190000` |
| `wp4_prior_jobs_hardening`         | `20260722191140` | `20260722190500` |
| `wp4b_photo_qa`                    | `20260722191802` | `20260722193000` |
| `wp6_export_guardrails`            | `20260722194033` | `20260722200000` |
| `phase1_actor_hardening`           | `20260723011122` | `20260723002255` |
| `qa_event_provenance`              | `20260723011144` | `20260723004439` |
| `public_h3_aggregates`             | `20260723011159` | `20260723005752` |
| `atomic_public_h3_refresh`         | `20260723011219` | `20260723010313` |
| `atomic_prior_attempt_claim`       | `20260723050851` | `20260723044745` |
| `document_authenticated_h3_role`   | `20260723050903` | `20260723045317` |
| `remove_public_submission_residue` | `20260723050918` | `20260723045606` |

Unchanged: `20260722164727`, `20260722164749`, `20260722164806`, `20260722170020`. Foreign identity: `20260730174047`. Canonical names and ordered files must still match the reviewed commit immediately before repair.

## Exact preparation and execution gates

The commands below use the installed **Supabase CLI 2.118.0**, whose local help supports explicit `--project-ref` and `--workdir`. Do not substitute the original workspace's older CLI. No password or connection URL is passed in command text. Justin authenticates with `supabase login`; credentials stay in the secret stores. Do not print debug output or dump contents.

The operational checkout currently contains the reviewed application chain. Before approval, confirm it remains clean at the bound source and repeat counts, schema comparison, ledger identities/digests, advisor and function inventory. Run `scripts/db-migration-test.sh` and the isolated reconciliation rehearsal; require thirteen expected migration assertions and the rehearsal's expected assertions, not an empty successful run. The existing thirteen assertions passed locally; hosted behavior still depends on CI and post-migration readback.

```sh
GSIP_REPO="/Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/repo"
GSIP_CLI="$GSIP_REPO/node_modules/.bin/supabase"
git -C "$GSIP_REPO" rev-parse HEAD
git -C "$GSIP_REPO" status --porcelain
"$GSIP_CLI" --version
"$GSIP_CLI" migration list --project-ref toxldjgwkxtneoqsazym --workdir "$GSIP_REPO"
```

Expected source is `f9e1ac2f8a88671f99b959e476499392297bd30f`, empty status, CLI `2.118.0`, and the original eighteen identities. Any different readback stops execution. The CLI may initialize its temporary database login role during read-only preflight; this is not an application migration.

Before any ledger repair, preserve the complete original history, including names and statement arrays, privately. Only migration metadata is dumped; do not dump application, auth, Vault or Storage rows. Create an owner-private directory outside the repository with restrictive permissions, never print its SQL, never attach it to a PR, and verify its eighteen rows in an isolated restore. A temporary file alone is insufficient recovery protection.

**Recovery preparation is now verified.** The owner-private copy is stored outside Git at `/Users/justinhart/.supabase/gsip-recovery/2026-10-11/`, directory mode 0700 and SQL file modes 0600. Its schema file is 1,116 bytes, SHA-256 `ae56295c7e66a8b46ab50df6f00cf57f7866f2478a17fbe3910d9def39e836ab`; its data file is 37,668 bytes, SHA-256 `612b05231c79eac1e52cc4bf5da49ec2e9d4755358b461c902af69f6f089c857`. A network-disabled isolated restore matched **18/18 complete records**, including names, versions, complete statement arrays and all six ledger fields, against fresh digest-only production queries. Exactly one user table and zero user functions were restored; recorded foreign SQL stayed inert text. The temporary container was removed. Gitleaks 8.21.2 scanned the private backup with zero findings and no custom suppression. Only sanitized receipts are in the review evidence directory; the SQL files are not attached or committed. Fresh ledger drift requires a new recovery copy and restore proof before any repair.

The following documents the read-only preparation pattern for a new copy; do not overwrite the verified files. Move any temporary copy into owner-private durable storage and verify that final copy before repair.

```sh
umask 077
GSIP_RECOVERY_DIR="$(mktemp -d /private/tmp/gsip-history-recovery.XXXXXX)"
"$GSIP_CLI" db dump --project-ref toxldjgwkxtneoqsazym --workdir "$GSIP_REPO" --schema supabase_migrations --file "$GSIP_RECOVERY_DIR/original-history-schema.sql"
"$GSIP_CLI" db dump --project-ref toxldjgwkxtneoqsazym --workdir "$GSIP_REPO" --schema supabase_migrations --data-only --file "$GSIP_RECOVERY_DIR/original-history.sql"
chmod 600 "$GSIP_RECOVERY_DIR/original-history-schema.sql"
chmod 600 "$GSIP_RECOVERY_DIR/original-history.sql"
shasum -a 256 "$GSIP_RECOVERY_DIR/original-history-schema.sql"
shasum -a 256 "$GSIP_RECOVERY_DIR/original-history.sql"
```

The checksums may be recorded; the contents remain private. This separate schema/data history backup follows [Supabase's documented history-preservation procedure](https://supabase.com/docs/guides/platform/migrating-within-supabase/backup-restore#preserving-migration-history), with flags checked against the installed CLI. Verify that the dump actually includes `supabase_migrations.schema_migrations` (the CLI can exclude managed schemas), contains exactly the original eighteen rows and restores their full statements/names in the disposable database. If it is empty, excludes history, or includes unrelated data, stop and prepare a reviewed alternative; never repair without a recoverable ledger. No foreign SQL is executed during restore: it is ledger text only.

**Gate A: Justin's explicit go for this exact history reconciliation.** Once the backup is durable and all fresh evidence agrees, run each command separately and read back the exact ledger set after each. No database push between repairs.

```sh
"$GSIP_CLI" migration repair --project-ref toxldjgwkxtneoqsazym --workdir "$GSIP_REPO" --status applied 20260722181500 20260722183000 20260722190000 20260722190500 20260722193000 20260722200000 20260723002255 20260723004439 20260723005752 20260723010313 20260723044745 20260723045317 20260723045606
"$GSIP_CLI" migration repair --project-ref toxldjgwkxtneoqsazym --workdir "$GSIP_REPO" --status reverted 20260722182403 20260722182446 20260722190912 20260722191140 20260722191802 20260722194033 20260723011122 20260723011144 20260723011159 20260723011219 20260723050851 20260723050903 20260723050918
"$GSIP_CLI" migration repair --project-ref toxldjgwkxtneoqsazym --workdir "$GSIP_REPO" --status reverted 20260730174047
"$GSIP_CLI" migration list --project-ref toxldjgwkxtneoqsazym --workdir "$GSIP_REPO"
"$GSIP_CLI" db push --project-ref toxldjgwkxtneoqsazym --workdir "$GSIP_REPO" --dry-run --skip-vault
```

Expected ledger sizes are 18 → 31 → 18 → 17. Adding canonical identities first leaves a recoverable, blocked duplicate state if interrupted. The sequence is not atomic. The CLI repairs history records rather than replaying the thirteen SQL files. Afterward, the baseline seventeen identity set must match exactly and application counts/schema/privacy protections must remain unchanged. The final dry run must list only the nine pending October files. `--skip-vault` avoids unrelated Vault changes. If a step fails, preserve its receipt and stop; no automatic retry, ledger rollback or DDL replay is authorized.

**Gate B: Justin's separate go to delete only the foreign Edge Function.**

```sh
"$GSIP_CLI" functions delete wavefunction-api --project-ref toxldjgwkxtneoqsazym --workdir "$GSIP_REPO"
```

Read back the inventory: `wavefunction-api` absent, intended GSIP functions unchanged. No application schema drop is proposed because both foreign tables are already absent. Function deletion is not reversible from this repository; the owner controls the separate application's source. History repair does not itself delete functions.

**Gate C: a subsequent, separate migration go.** The pending files are:

1. `20261010120000_wp6b_capture_gate.sql`
2. `20261010120100_wp6b_path_binding.sql`
3. `20261010120200_wp6b_finalize_and_settle.sql`
4. `20261010120300_wp6b_k_anonymous_cells.sql`
5. `20261010120400_wp6b_attribution_and_metadata.sql`
6. `20261010130000_wp6c_priors.sql`
7. `20261010140000_wp6d_contributor_rights.sql`
8. `20261010150000_wp6e_provenance.sql`
9. `20261011090000_wp_agent1_releases.sql`

After Gates A/B are verified, present their exact plan and `db push --skip-vault` command again and wait for the migration go. Then follow [PHASE1_DEPLOYMENT.md](PHASE1_DEPLOYMENT.md), including zero advisor findings and live `capture_open = false`. Edge deployment, variables, worker dispatch and Pages each remain gated. The `main` Pages workflow currently deploys automatically; protected deployment approval must be reconciled with Justin before merges cause a production deployment.

## Assumptions and limits

Justin's target and foreign-deployment attribution are authoritative owner decisions. Seed classification is his statement; independent evidence establishes aggregate counts, not contributor-row provenance. No concurrent application or ledger writer is assumed, and fresh checks must invalidate this plan if state changes. Strict effective-schema equality does not reconstruct past DML effects or prove the complete hosted platform identical to local stand-ins. Platform extensions/grants stay intact. History repair, function deletion, nine new migrations, anonymous-auth readback and physical-device backup tests remain unexecuted gates. No new dependency, service, licence or architecture is introduced.
