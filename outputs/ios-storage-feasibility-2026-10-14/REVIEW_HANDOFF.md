# APP-2C1 source-only feasibility handoff — 2026-10-14

Justin explicitly approved merging #68 and continuing iOS storage feasibility, while preserving the production/capture hold.

## Source state

- [#68](https://github.com/global-soil-intelligence/gsip/pull/68) merged as `883c7ee51dcb6c58cb7f309b78a590ea684ba8c7`; merged-main CI38642693289 and scanner38642693189 passed.
- [#69](https://github.com/global-soil-intelligence/gsip/pull/69) is open, unmerged, at `258b57732a94968e576eb15e848566a487cb4878`, branch `wp-app-2c1-storage-feasibility`. Required hosted validation38644748460 passed at that exact head; both secret scans passed. DCO was skipped by the existing workflow. CI:2,006 Python passes/31 skips,12 browser passes,mypy78files,593 pgTAP assertions/11files, Deno, migration13/13+19/19+13/13 and all lint/typecheck/JavaScript/build/map-budget/database lifecycle steps passed. SOURCE_CLOSEOUT.json and HOSTED_CI.json preserve exact run/check metadata; full logs were not persisted.
- Final reviewed manifest `4dce6b0fc9fa8c14d8a7e7943fbe0077c8fec97cc45802a66a84305e44cbe975`: all372 declared blobs/modes,364 existing unchanged,8 authorized paths changed. SPEC line9 onward unchanged; only the three APP-2C1 acceptance boxes changed among132 prior lines.

## Built and verified

An offline Python checker verifies19 exact public dependency source snapshots and13 application/lockfile sources. Valid evidence deliberately returns exit3/statusblocked; backend_selected,storage_feasible,migration_implemented anddevice_verified remain false. No caller capability manifest, native/web fallback or readiness result exists. The public input catalog contains precise archive/member/hash origins and a normalized observed generated resolution with original-byte provenance; that resolution is not a repository-native lock or proof of every build.

Complete current persistence scope and14 negative/unproven capability findings are documented. Existing package and four unadopted component licences, maintenance dates and compressed/unpacked source sizes are recorded. SQLite offers transactions but lacks the required exclusion/readback/lifecycle/privacy closure. Preferences, session Keychain storage and managed browser windows do not solve the complete app-host/queue contract. No candidate was installed or selected. Manual archive facts are separate from the byte checker's guarantees.

Local full lint, Ruff, strict mypy78files and diff checks passed. Focused77tests passed with no skips; all38new tests failed on unchanged baseline with0errors/0skips. Independent review repeated those results and caught five guard-removal mutants. Root and independent actual-source replays verified19+13inputs and correctly returned blocked. Independent commit closure verifies exact parent, all source hashes/modes, required metadata and no Signed-off-by. Gitleaks8.21.2 scanned non-shallow all-ref history with redaction:158reported commits,0findings; exactly the same four approved historical fixture suppressions and configuration hashes.

## Changes after review

1. Corrected displayed resolution length/hash to the actual normalized1233-byte profile; original1260-byte provenance remains explicit. Failing-before/passing-after table regression retained.
2. Corrected a local evidence end-line159 to actual157; added a failing-before range regression.
3. Qualified browser-store behavior by iOS17+/shared/older mode and separated manual archive metadata review from checker source validation.

## Remaining gate and assumptions

APP-2C1 is complete as a documented blocked feasibility result. APP-2C2 cannot start until an exact supported backend/transaction/host-lifecycle mechanism is independently reviewed and approved. No candidate currently warrants selection or a native-language exception request. Any custom native implementation needs Justin's separate explicit exception to TypeScript/Python-only. APP-2C3 requires a reviewed implementation plus separately authorized synthetic physical-device/account/signing inputs. Source, simulator or CI passes do not prove backup exclusion or physical erasure.

The fixed13-file read set plus manually reviewed current inventory does not automatically discover every future unbound persistence feature. Future source/version/new-surface changes need fresh review. The POSIX reader checks bounded reads/races, not a universal snapshot or changes after return. Old provider-held backups cannot be retroactively retracted. Package source sizes do not establish native/transitive/app binary size or full licence/provenance closure. No new dependency/service/licence is selected.

## Production checklist for this turn

No production migration, Edge Function deployment, repository-variable change, worker/export/tile dispatch, Pages approval, capture/sign-in opening, account/signing action, native/device experiment or real app-data read occurred. Existing database/function/service state was not re-queried and no production-health claim is made. Pages for merge883 is waiting behind sole reviewer jdhart81 with admin bypass disabled; all five schedule guards were absent/held before merge. Pending legal/store, calibration/photo publication, capture and launch decisions remain separate.
