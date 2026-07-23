# Canonical GSIP catalog authority and reconciliation evidence

All work here is local preparation or comparison of previously collected schema metadata. No contributor-record read, production history repair, function deletion, deployment, source-worktree edit or capture/auth change was performed. Intended closed capture/auth policy is not a readback of current production settings.

## Canonical stages and provenance

Reviewed source: `f9e1ac2f8a88671f99b959e476499392297bd30f`. Local PostgreSQL `17.6`; installed image `public.ecr.aws/supabase/postgres@sha256:ca7871b587ca2c401ac0f325df6249c9aa0d25647ded34631158efc51176767f`. The source mount was read-only; network was disabled; user was `postgres`; no host ports or production credentials were supplied. No seed fixtures were used for the canonical catalog exports.

The first seventeen July migrations produce the pre-upgrade GSIP baseline. Nine later reviewed migrations produce the v3 target. Source files are read from the bound Git commit, not copied from private foreign application source. The auth/Storage tables and auth.uid(), auth.role(), storage.foldername() are repository stand-ins, not authoritative hosted platform function bodies. Stand-in default ACLs are a reference setup; platform differences remain explicitly scoped.

Extractor v2 includes table/function owners, security-definer flags, volatility, search paths, function definition SHA-256, nested function privilege delegation, columns/types/defaults/nullability, constraints/FKs and validation state, indexes, RLS/policies, grants and triggers. Supplemental metadata includes private functions, public view identity/options/hash, schema ACLs and storage.objects ownership policies. Function bodies and application row values are omitted.

| Stage | Tables | Columns | Constraints | Policies | Public functions | Private functions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Completed July baseline (17) | 11 | 96 | 62 | 16 | 5 | 2 |
| Reviewed v3 target (26) | 20 | 162 | 126 | 24 | 19 | 22 |

## Three historical source differences

**wp1_schema.** Compare the cumulative seventeen-migration result, not the initial CREATE statements. Licensing moved from contributor terms fields into immutable contribution_grants, and submissions use the non-null composite grant-owner FK. Geometry remains private geometry(Point,4326). H3 hints become nullable, resolution-checked, cleared for client writes and required for qa_pass. Later migrations establish units/depth bounds, server-only synthetic classification, GPS accuracy and QA provenance. The current production columns, constraints, indexes and table/RLS metadata match this completed baseline exactly. No schema replay follows from a historical statement-digest difference.

**wp1_rls.** The initial security-definer contributor lookup and anonymous per-submission grants are superseded by the later July chain: stable SECURITY INVOKER current_contributor_id(), narrow client column writes, pending-only owned inserts, private server queues, and removal of public_submissions and its anonymous policy. Current production differs only by six exact bound relation aliases. Public/private function hashes, owners, execution delegation, grants, triggers, Storage policies and public-view absence otherwise match. The two predicates are alpha-equivalent SQL, and local behavior tests prove own reads/inserts work while foreign/anonymous/client-metadata/queue access is denied for both variants. Preserve the existing predicates; do not rewrite RLS for text equality.

**wp4b_photo_qa.** The recorded remote historical statement SHA matches the older repository file at `969076a394aef4af8c65b55a664001b68fc2bfa6`. The current local file adds only IF NOT EXISTS to `ADD COLUMN gps_accuracy_m`: the column is nullable REAL with a validated nonnegative check, not a boolean or a GPS-stripping flag. The canonical column/constraint/grant and photo-QA jobs, trigger, function security/owner/privileges now match production. IF NOT EXISTS alone would not repair a missing check or wrong type, but the metadata comparison independently confirms the correct final definition. Do not rerun already-applied QA DDL.

Justin reports fourteen historical bodies differ only in comments/whitespace and three substantively. This is owner-supplied source provenance; exact/outer-whitespace digest checks establish a subset independently. Strict current-catalog equality does not reconstruct historical DML effects or establish provenance of live rows. The thirteen timestamp pairs below therefore remain a separately gated metadata reconciliation, with private recoverable history backup and fresh evidence required.

## Strict equivalence proof

One positive comparison passes across all ten primary and four supplemental metadata sections. It allows only six exact recorded ownership-expression substitutions in the six named policies, the three exact hosted-platform extensions (pg_stat_statements 1.11, supabase_vault 0.3.1, uuid-ossp 1.1), and three exact platform schema grants. Everything else must match. Nine negative controls reject a private anonymous grant, OR-true ownership predicate, missing grant FK, definer contributor lookup, unknown extension, private-schema anonymous usage, changed function owner, changed table owner and changed function privilege delegation. No broad SQL normalization or security weakening is used.

## Disposable ledger and upgrade rehearsal

`rehearse-catalog-repair.py` and all generated coordinate-free SQL inputs are preserved outside the source checkout. Synthetic submissions use POINT EMPTY, not coordinate literals. The historical ledger is fabricated from names/versions with NULL statement arrays; no Wavefunction SQL is imported or executed. The driver models documented ledger insert/delete effects in SQL; it does not execute the Supabase CLI, production repair or function deletion.

All **64/64 expected assertions** pass. Forty test canonical/deployed-alias ownership behavior. The unsafe permissive-policy negative control must fail with the specific own-row visibility error, not an arbitrary tool error. Ledger assertions cover 18 → 31 → 18 → 17; public catalog, private/view/Storage metadata, synthetic row digests and an unrelated sentinel remain unchanged through metadata changes. Applying only the nine pending migrations produces the exact 26-identity ledger and reviewed target catalog. Five exact SELECT aliases survive; photo INSERT is replaced by the reviewed migration. Eight additional assertions cover legacy row counts, synthetic actor/photo tiers, finalize/QA backfill, immutable old receipt times, and local capture_open=false. The unrelated sentinel survives the upgrade. Negative ledger controls reject removal of an unchanged identity and marking an October identity applied prematurely.

Zero pgTAP assertions are reported by this task. The mandatory existing `scripts/db-migration-test.sh` thirteen-assertion test remains separate; this rehearsal does not substitute for hosted RLS behavior checks or recoverable original-ledger verification. The v3 target intentionally keeps contribution_grants_attribution_safe NOT VALID for legacy attribution review; exact validation-state comparison preserves that reviewed choice, without falsely claiming every target constraint is validated.

## Timestamp pairs (prepared only)

| Name | Recorded remote | Canonical local |
| --- | --- | --- |
| wp1_v22_privacy_and_grants | 20260722182403 | 20260722181500 |
| wp1_performance_indexes | 20260722182446 | 20260722183000 |
| wp4_prior_jobs | 20260722190912 | 20260722190000 |
| wp4_prior_jobs_hardening | 20260722191140 | 20260722190500 |
| wp4b_photo_qa | 20260722191802 | 20260722193000 |
| wp6_export_guardrails | 20260722194033 | 20260722200000 |
| phase1_actor_hardening | 20260723011122 | 20260723002255 |
| qa_event_provenance | 20260723011144 | 20260723004439 |
| public_h3_aggregates | 20260723011159 | 20260723005752 |
| atomic_public_h3_refresh | 20260723011219 | 20260723010313 |
| atomic_prior_attempt_claim | 20260723050851 | 20260723044745 |
| document_authenticated_h3_role | 20260723050903 | 20260723045317 |
| remove_public_submission_residue | 20260723050918 | 20260723045606 |

The first four identities are unchanged. The accidental foreign identity `20260730174047_wavefunction_beta_schema` is separate; its ledger retirement and deletion of the owner-identified 410 stub require exact commands, exact target and Justin go. No foreign source belongs in GSIP.

## Receipt hashes

- `canonical-catalog-source-receipt.json`: `e554279c18e7d28410bce91f51bed53bfe2f22f7a22fe53fcf2f8a66683b4b14`.
- `canonical-catalog-baseline17.json`: `83b9702c433bbcd0b37382bc85a61767c262f64d0caefeec4902322929b0ffca`.
- `canonical-catalog-baseline17-supplement.json`: `dd8bdda47d262ef2e86e1679d55c45de8cdf706e4b3f394272c88997e9a7fb7d`.
- `canonical-catalog-target26.json`: `eca562018a82a5df9f2ddd37b1f47e81a26be709f34e4b967c21d5442a562393`.
- `canonical-catalog-target26-supplement.json`: `1ea270359d6b9587d1dc444e9196cc4628c49d21047fa4d0604cfc0925ea136d`.
- `canonical-production-equivalence-proof.json`: `bcd6248b94c5055555598f4e5c9e508abec4619eaf22bacbbcb07af1916506aa`.
- `canonical-migration-timestamp-map.json`: `e2c5756b62a73298aaaa18ef8b0c0a6398d2cb37fcecc885555cef2799d9fcf0`.
- `canonical-ledger-reconciliation-rehearsal.json`: `4080346f1d0935d3bc93a428df227eaf7380450f03be7c2e1e1dcd6591372cef`.
- `build-catalog-references.py`: `fadac4bc237b54e083c16ef1a31799379e59fdadfd8d111b45bb7cf51f81eb16`.
- `assert-catalog-equivalence.py`: `14a7a137aecb16df19fdb0db0ffc5d2383e7ec824405af227bab632973013ae5`.
- `rehearse-catalog-repair.py`: `f3a3698cb9dc6efeb18a3d621dfceb3ab7c7b4a0c24c294e8d29b2cfce290f0c`.
- `photo-qa-historical-source-proof.json`: `51e5165c3f0b19d51f1a08fad8e8ae2148837355fb19c62713447819a5f34d0c`.
