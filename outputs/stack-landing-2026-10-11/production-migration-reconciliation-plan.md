> Historical preparation note. Superseded by green PR #40 at cf063aa and docs/PRODUCTION_RECONCILIATION.md. See REPORT-current.md for verified backup/restore evidence and pending Gate A/B approvals. No repair or deployment has run.

# GSIP production migration reconciliation — proposed, not executed

Target: `toxldjgwkxtneoqsazym` (owner-selected canonical project). Audited 2026-10-11. This is an operational plan outside the source branch, not permission to migrate or repair production. No contributor rows or SQL statement bodies were fetched by this review; comparison uses local Git source and the root agent's counts/digest receipts. Justin requires capture and production anonymous sign-in to stay closed. The live capture-gate table is absent and anonymous-auth configuration is unverified; neither closed state is asserted as a completed readback.

## Confirmed evidence and current blocker

The reviewed local tip has **26 migrations: 17 July baseline + 9 WP-6b through WP-AGENT-1 additions**. The restored target records **18 applied migrations: those 17 baseline names plus `20260730174047_wavefunction_beta_schema`**, absent locally. Four baseline timestamps match; thirteen differ. The root's dry run exited **1 / DbPushMissingLocalError**, so no migrations were pushed. Its generic suggestion to mark fourteen remote versions reverted must not be followed blindly.

Independent local comparison reproduced **4 exact byte matches + 7 matches after trimming only outer whitespace + 6 differing SQL digests + 1 remote-only migration**. The first four migrations have matching versions but differing statement digests: timestamp alignment cannot establish equivalence. Do not normalize away quoted strings, identifiers, dollar-quoted function bodies or statement order to manufacture a digest match.

| Differing baseline name | Evidence / next classification |
| --- | --- |
| `wp1_extensions` | No matching historical Git blob; extension locations/versions remain unverified. |
| `wp1_schema` | No matching historical Git blob; relation/column/constraint and data-statement equivalence remains unverified. |
| `wp1_rls` | No matching historical Git blob; RLS, grants, policies and function security remain unverified. |
| `wp1_review_hardening` | No matching historical Git blob; constraints/policy equivalence remains unverified. |
| `wp1_performance_indexes` | No matching historical Git blob; index definition equivalence remains unverified. |
| `wp4b_photo_qa` | Remote SHA256 exactly matches local Git source at `969076a394aef4af8c65b55a664001b68fc2bfa6`. The only later source delta adds `IF NOT EXISTS` to the `gps_accuracy_m` column addition. Confirm the actual column type/check/grants before classifying the difference as harmless. |

The five unmatched names were checked against every locally available historical blob of their canonical path; each had one distinct blob. The photo-QA path had two. This search does not cover unknown external handoffs or source repositories. A digest mismatch alone proves neither a schema difference nor safety.

## Safest next steps

1. Preserve the existing ledger, statement digests and counts as immutable receipts. Root has a pending question for Justin about the authoritative `wavefunction_beta_schema` source; do not ask twice or invent a placeholder/no-op migration.
2. Obtain authoritative source for the remote-only migration and unresolved five baseline statements. Match it to the recorded digests in a private, secret-safe comparison; classify DDL, DML, triggers/functions, dependencies, grants/RLS and ownership without publishing statement bodies or private payloads. Catalog digests can corroborate schema state but cannot prove historical data effects by themselves.
3. Preserve every unknown/other-project object and all data. If the extra migration belongs to another application, document that boundary and its exposure before choosing a reconciliation. Do not drop it, mark it reverted, or import unreviewed SQL into GSIP solely to silence the CLI.
4. Prefer a **forward, reviewed reconciliation work package** that adopts the verified deployed baseline identities/order and explicitly handles the extra migration, leaving the original reviewed commits intact. If substantive schema differences exist, design the smallest prerequisite-compatible forward fix rather than replay an already applied migration. The exact implementation depends on the missing source evidence; no rename, baseline import or schema fix has been performed. Local preparation can continue within the user's task authority once that evidence is available; production mutation still requires separate exact-command approval.
5. A narrowly mapped production-history repair is a fallback only after full source/order/schema proof and a disposable rehearsal. Repair changes history records, not schema: retain the original ledger, map each old/new version explicitly, preserve the extra entry, show exact target/commands and wait for Justin's separate "go". No blind `repair`, `--include-all`, squash or production reset.
6. After reconciliation, a dry run must list **exactly the nine genuinely pending reviewed additions** (plus any separately reviewed, explicitly justified correction), in the intended dependency order, with no July replay or unexplained omission. Then run the required migration test and request production authorization; dry-run success alone is insufficient.

Supabase compares migration timestamps rather than SQL contents, and applied/reverted repair inserts/deletes ledger entries. [Official CLI reference](https://supabase.com/docs/reference/cli/supabase-migration-repair). The installed repository CLI runs under the root's configured runtime; this review did not establish a working standalone CLI invocation and proposes no new production command flags.

## Meaningful disposable rehearsal — not yet run

Run both the mandatory **checked-in** `scripts/db-migration-test.sh` and a separate drift rehearsal. The existing script applies only local files with a synthetic pre-WP-6e fixture and a Supabase stand-in; its 13 assertions do not reproduce the target's extra migration or prove full hosted Auth/Storage compatibility.

For the drift rehearsal, use isolated disposable PostgreSQL/Supabase matching the target's recorded major/minor and extension versions, with no production network route or real contributor data. After reviewing the SQL for side effects, construct the **verified actual eighteen-migration baseline** and its history, seed synthetic legacy contributors/submissions/photos/jobs/grants, and apply the proposed identity reconciliation and pending additions through the same CLI path planned for production. This is not a restoration of production rows. A schema-only copy is supporting evidence, not a substitute for known historical data effects.

Prove: the unaligned history fails safely; corrected dry-run selection is exact; already applied SQL is never rerun; all pending migrations apply; legitimate synthetic records survive/backfill correctly; capture stays false and production auth policy is untouched; RLS/grants and all pgTAP assertions pass; GSIP-owned catalog definitions converge to the reviewed reference; unrelated extra-object digests/counts remain unchanged; a second dry run has no pending migration. Include negative controls for a missing history entry, differing statement digest and altered constraint/policy. Require a nonzero planned assertion count: the current shell runner can print `0/0 ok` for an empty test result, so its comment claiming missing-assertion detection is not sufficient proof.

Record command exits, test counts, sanitized catalog/count comparisons and digests only. No images, precise points, sessions, secrets or row payloads enter fixtures, logs or receipts. Public photo/dataset/worker/Pages deployment remains separately gated. Unknown statements or a failed rehearsal keep production migration blocked.

## Evidence receipts

- [production-restored-preflight.json](production-restored-preflight.json) — SHA256 `2e55669c0af3f2dfb3a6f9cc3f3c5f7867aeec3c1b1409c4c2c64f86a9d1c053`.
- [production-additional-schema-counts.json](production-additional-schema-counts.json) — SHA256 `c658b90e465707ef445ca39d8fcd359427dd09d8d1ae83af32997079bf27f640`.
- [production-migration-statement-sha256.json](production-migration-statement-sha256.json) — SHA256 `7b8429f2e00f19f495cd439ae98d7465637c5fcde1d8c8d9a4a1053025f10eee`.
- [production-migration-dry-run.json](production-migration-dry-run.json) — SHA256 `95d30fb8cfb06c4e859ac361d4d74c7294ad75c8d9ae81138979c11eead477c3`.
