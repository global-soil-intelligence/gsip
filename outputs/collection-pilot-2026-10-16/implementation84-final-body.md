## Problem and result

WP-COLLECT-2 (#82): the existing capture client relied on anonymous first-use sign-in, a closed artifact hid withdrawal, and manual export/public-cell paths were not a collection-only boundary. This adds the source for an **invited adult phone-browser pilot** using existing owner-provisioned accounts, immutable private records, existing-account recovery, and rights access after intake closes.

Stacked on #83 (SPEC v15), which specifies the architecture before this implementation. Implements #82's source/testing scope; #82 remains open for separately authorized operations and a real consenting-participant phone rehearsal.

## Invariants and added behavior

- I1–I15 and B1–B8 remain binding. No contributor contents, real coordinates, credentials or private metadata in evidence. MIT / ODbL 1.0 / CC BY-SA 4.0 unchanged; no dependency or paid/closed service added.
- Owner-only private membership, a verified non-anonymous existing account and **both** current capture/library gates admit every contributor write, upload, finalization and private intake. Restrictive policies preserve existing RLS; locks serialize membership revocation/intake closure against writes.
- Every new submission is server-classified `private_pilot`, even for service callers or when library context is omitted. Existing rows backfill `legacy`; neither client nor worker can promote a pilot row. Existing grants, withdrawal-first rules, quotas and owner reads remain effective.
- Fixed service-only publication refusal blocks export, manual public-cell refresh and positive cell/release writes. The exporter refuses before candidates/photos/cache/Hub and at publish boundaries; real REST and pure APIs reject pilot/unknown/missing classification. There is no publication-enable switch.
- Existing-account email sign-in/recovery sets `shouldCreateUser: false`, with no anonymous fallback in pilot/rights views. Auth/view/queue-generation fences prevent wrong-account writes, stale queue resurrection and destructive cross-account cleanup; holds preserve retry budgets.
- Explicit browser `#your-data` / `?view=your-data` recovery remains available in a false/false artifact. Default closed landing and native startup do not start auth or network. Confirmed deletion clears local private bytes before its legitimate sign-out; account changes cancel stale confirmations.
- Default Pages/native packaging retains its exact closed manifest. A separate source/target-bound browser candidate path and manually dispatched **artifact-only** workflow require exact clean main source and protected owner approval. No deployment permission/step or automatic activation. Synthetic `.test` fixtures stay temporary and loopback-only and cannot be packaged for deployment.
- Operator handoff: `docs/COLLECTION_PILOT_OPERATIONS.md`. Relative to the dated 28-entry baseline it identifies **three** pending migrations (LIB4, WP-6fA, COLLECT-2), requiring a fresh dry-run/counts/advisors and separate owner go. No production, account, membership, Auth, worker, migration, deployment or activation operation ran for this PR.

## Changes after review

- Rejected omitted scope in the pure export API instead of silently treating it as legacy; existing synthetic legacy fixtures now declare their scope explicitly.
- Added `.xml` to the bounded artifact types because the real closed site includes `sitemap.xml`; regression proves it is retained and hashed.
- Closed the stale-admission/account-switch and confirmed-delete sign-out races with deferred-response regressions and identity checks at write/cleanup boundaries.
- Distinguished an unused provisioned sign-in account from no session; the truthful organizer deletion fallback creates no contributor through closed gates. Confirmed server requests now stay confirmed when local cleanup fails, with pending cleanup reported separately.
- Keyed My Soil by the auth epoch to discard old-account results; pilot copy explicitly holds records from public maps/exports and never promises automatic account creation or publication.
- Isolated historical iOS feasibility unit fixtures from mutable current application files. The sealed production profile/hashes are unchanged; synthetic fixtures explicitly cannot renew its historical source audit or any native/device acceptance.

## Verification

- `pnpm lint`, `pnpm typecheck`, `pnpm test`: pass; **689 unit tests** (332 capture, 308 schema, 33 site, 16 map).
- Complete local Python suite: **2162 passed / 35 skipped** out of 2197 collected. Ruff and mypy (83 source files) pass. GDAL is unavailable in the host shell; CI retains `GSIP_REQUIRE_GDAL=1`.
- Isolated network-disabled PostgreSQL16/PostGIS/pgTAP: **632 role assertions**, **61 populated-migration assertions** and **43 concurrency scenarios** pass. Negative baseline fails without the migration. No production credentials/ports/network in that proof.
- Closed web build, map/site budgets and native web build pass; both ordinary activation receipts remain exactly false/false. No canonical open pilot artifact generated.
- Gitleaks **8.21.2** scans final changed/new source with zero findings; base full-history scan covers 180 commits with zero findings. Scanner policy, history/redaction and approved fingerprints unchanged.
- Independent cross-review found no remaining issues after the corrections above; reviewer independently ran 85 export/artifact tests and 96 focused frontend/rights tests.
- Synthetic full desktop/emulated Android/emulated iPhone browser matrix passed 48/48 before final review corrections; final repeat and exact-head hosted CI/native artifacts are tracked below. Actual email/device/hosted operations remain unverified.

Required checks remain effective. CI adds emulated Android Chromium/iPhone WebKit coverage while retaining desktop, database, GDAL, native, dependency, permission and secret checks.

## Assumptions and limits

- Justin's 2026-10-16 go selects invited adult browser source work with existing owner-provisioned accounts. It authorizes neither creating an account nor opening collection. Pilot capacity/duration and hosted notices/version/support remain separate owner inputs.
- The production baseline in the handoff is dated evidence, not a new readiness claim. Fresh counts, advisor/Auth/Storage/worker checks, exact migration/artifact commands and a separate go are required before each production step.
- Browser-engine emulation and synthetic SDK/server tests are not physical-phone, actual delivered-email, hosted sanitization/deletion or native backup/device proof. Those rehearsals remain held.
- Intake covers A+B photographs, context and optional bounded instrument-declaration JSON. Original spectral files/lab reports, verified physical pairing, field feature extraction/model training, real federation and public spectral/photo release remain separate packages/gates.
- Outside counsel is not a collection prerequisite under the adopted owner policy. Complete notices, personal contributor acceptance, privacy/licences, factual disclosures and technical gates remain required.
- Capture/library uploads and all publication remain closed in production. Merge and deployment require separate owner authorization.

## Final committed-source and CI evidence

Exact head `273ba98704343339c174a31124b887e19ead3dca`: [validation run 38981525926](https://github.com/global-soil-intelligence/gsip/actions/runs/38981525926) and [App build 38981525934](https://github.com/global-soil-intelligence/gsip/actions/runs/38981525934) passed. Android, iOS and both secret scans are green; internal-branch DCO was skipped, not certified.

- Final local browser matrix after all review corrections: **48/48** on desktop Chromium and emulated Android Chromium/iPhone WebKit. CI separately passed **16 desktop + 4 invited phone-browser tests**.
- CI Python: **2166 passed / 31 skipped** (existing opt-in real-Gradle controls); GDAL-required tests and Deno passed. Actual native build, permission/dependency/license audits and repeated-build checks passed in the app job. This does not claim opt-in controls or physical-device/backup acceptance ran.
- CI: **61 populated-migration assertions**, **43/43 concurrency scenarios** and **632/632 Supabase role assertions** in 12 files passed. Race proofs explicitly report production access false.
- Both [native artifacts](https://github.com/global-soil-intelligence/gsip/actions/runs/38981525934) exist, are unexpired and bind to this head: Android debug **12082075116** (29,125,224 bytes; SHA256 `ec8fda8409ed01676adbb4838aefb3ad4f394b354b1fadc4a4165dfcdef1f45b`) and iOS simulator **12080949345** (13,920,118 bytes; SHA256 `82543e2c0c9c365c143fcdfe10b549b4f031335e07f869ce98bf8b7470e1a407`). These are CI artifacts, not production/store releases.
- Gitleaks **8.21.2** with `--all --full-history --redact`: **181 commits, no leaks** including this commit; no scanner rules/workflow/redaction/history coverage/suppressions changed.
- Final committed-source closed Pages/native web builds and both budgets passed. Public live activation receipt read on 2026-10-16 remained exactly `capture_live=false`, `library_intake_live=false`. Merge-triggered Pages runs are cancelled. No canonical invited artifact, production migration/deployment/account operation or activation ran.

No open independent-review findings. #82 remains open for separate hosted operations and a consenting-participant physical-phone rehearsal. Review #83 before #84; further merges and production/collection activation require the owner's separate go.

