## Proposed amendment

Schedules the account-free WP-APP-2A build and backup work, WP-APP-2B local notifications, and WP-6f screening of every publishable photo. Records Justin's chosen policies: exclude private cloud backups; allow cleanly separated Android direct transfer; withhold only flagged photos for private human review; no automatic blur.

The reviewed v3.0 header/status and SPEC sections 1–13 remain intact. Section 15 is a pending v4.0 proposal. Notification architecture and detector screening remain unimplemented. **WP-6f may start only after Justin approves and merges this specification PR.** Already-authorized APP-2A preparation can proceed on this commit, with its merge following this specification.

## Invariants

I1–I15 and B1–B8, MIT/ODbL 1.0/CC BY-SA 4.0, TypeScript/Python, public anonymous agent reads and strong RLS continue to hold. Capture and production anonymous sign-in remain closed. No dependency, model, migration, service, signing material or production setting is added. Every production command still needs its exact-target go. Justin reviews and merges.

## Review evidence

- Existing language guard and whitespace check passed using the bundled supported Node runtime.
- Seven local document links/anchors resolve; scoped formatting checks pass.
- Compared SPEC sections 1–13 with the reviewed base: unchanged.
- Dependency comparison cites primary sources and distinguishes code licenses from model-weight licenses; records maintenance and payload size without claiming runtime size or GSIP recall.

## Assumptions and unresolved gates

- Local notifications are a proposed MIT plugin, requiring a fresh pinned/transitive audit, measured artifact impact, inexact scheduling and unchanged-strength Android dependency/permission checks in the implementation PR.
- Public coverage alone does not establish land access or absence of withheld observations; nearby suggestions stay disabled unless eligibility inputs support them.
- Current WebKit IndexedDB/localStorage iOS backup exclusion is unproven. A separate storage design or approved native-language exception and synthetic physical-device backup/restore evidence are required.
- Open face/text candidates are for private benchmarking; no complete calibrated detector set is selected. Plate-weight licensing, global category coverage, high-recall calibration and runtime size remain gates.
- Owner policy choices are not deployment approval or approval of an unreviewed screening implementation. No real contributor data is used.


## Changes after review — owner revisions (2026-10-12)

- Added SPEC §11 photo-publication gate: WP-6f must be deployed and Justin must approve calibration before any photo publication; newly built releases remain structured-data-only with empty photo lists until then. Existing QA/reviewer clearance cannot bypass this gate.
- Scene-text screening may exclude only the reliably detected GSIP reference-card quad plus a bounded, versioned margin from the existing marker homography. Faces cover the whole frame; failed card localization screens all text. Everything outside the card exclusion is screened.
- Start with face and scene-text detection. A dedicated plate model requires a staged material-gap finding and verified code/weight licenses.
- WP-APP-2B version 1 schedules sync reminders only. Nearby suggestions wait for Most Wanted and land-access eligibility inputs. This supersedes earlier nearby-v1 proposal wording in the preserved description.
- Kept APP-2A’s existing comparison, CI versions and backup rules. No model/plugin, detector implementation, migration or production action.

Validation: 13 meaningful policy checks failed before edits; all 15 now pass. Full local Python: 235 passed, 4 GDAL skips; initial full-run HF cache permission failures resolved by a private temporary cache, without source changes. Ruff/mypy, formatting, language guard and link checks pass; independent review passes. Current-head CI is pending.

Assumptions: gate applies to every newly built release; no retroactive erasure of immutable releases is claimed. No capture-opening authority changes. Card margin/calibration and model selection remain implementation gates. Current export code does not implement data-only suppression: photo-capable worker/export dispatch stays blocked until enforcement exists. iOS device backup proof remains pending.


## Changes after review — current-head CI closeout (2026-10-12)

- Exact reviewed head: `bc1a2938cbb17feaca44a611fe04fd406713f3d3`. The current-head [CI validate run](https://github.com/global-soil-intelligence/gsip/actions/runs/38248716454) completed successfully. The current-head [secret scan](https://github.com/global-soil-intelligence/gsip/actions/runs/38248716442) also completed successfully.
- The pending-CI statement in the preceding preserved section is superseded by this successful current-head readback. This remains a specification proposal; implementation and launch gates still require their stated evidence and Justin’s decisions.
- DCO is **SKIPPED**, as shown by the current-head check. A skipped DCO job is not a passing DCO certification, and no agent Signed-off-by for Justin was added.
- This update records validation evidence only. It changes no source, dependencies, signing inputs, permissions, deployment state or merge authority.


### Security-boundary correction and exact-head CI (2026-10-12)

Current head: `322ecd44fa20688b9c24229f719c5e8c6733aba8`. Existing description and earlier verification records are preserved above.

Inherited change: merge-forward carries #28’s spec-first boundary clarification and #29/#31’s additive guarded-helper/invoker and restrictive-policy fixes. The owning fixes remain on WP-6b/WP-6d; this branch does not duplicate or rewrite their SQL.

The hosted Gate C zero-findings check stopped on seven findings across the service-only rights tables and client-executable public definer functions. The correction preserves authorization rather than suppressing any advisor rule. All 26 executed migration blobs remain unchanged. No new client schema, table or column grant is added; narrow EXECUTE grants on new private helpers match the existing public callers. Public signatures and caller ACLs, owner checks, withdrawal refusal and capture-closed behavior remain intact.

Local source proof preserved the existing WP-6b 99 assertions and WP-6d 209 assertions; the new owning suites passed 16 and 21 assertions respectively, with 13 new assertions failing before the changes. The candidate complete pgTAP suite passed 299 assertions, migration testing passed 13/13, and isolated synthetic PostgREST dispatch/reload/privilege tests passed 33/33. These are local proofs; hosted advisor remediation remains unexecuted.

Exact-head CI, verified 2026-10-12 14:56:50 UTC: [validate — SUCCESS](https://github.com/global-soil-intelligence/gsip/actions/runs/38265398120/job/114866167097), [gitleaks — SUCCESS](https://github.com/global-soil-intelligence/gsip/actions/runs/38265398198/job/114866167358). All 13 updated PR heads are green for their required checks. DCO is SKIPPED; an agent has not certified Justin’s DCO.

Assumptions: the reviewed migration owner and exposed-schema settings remain unchanged and there is no overlapping production writer; production execution must refresh these checks. Private is absent from the observed Data API exposed-schema list, but schema placement alone is not authorization. Local tests use synthetic data and do not establish the hosted advisor’s final state. Capture, sign-up and anonymous sign-in stay closed; no production mutation, deployment, new dependency, service or licence change is included in this update.


### Changes after review — owner merge exception and worker holds (2026-10-12)

Justin explicitly authorised removing the extra approving-review requirement for this owner-operated repository. Independent review, green CI, resolved conversations and protection against force pushes remain required. Agents do not submit approving reviews or certify the DCO.
Scheduled production workers now require their own explicit repository-variable opt-in; absent variables hold jobs before any secret-bearing step. Manual dispatch still requires a separate production gate. Contributor-rights schedules receive the same hold from WP-6d onward. This prevents merging workflows or adding a credential from starting unapproved production work. Regression tests failed before the relevant change and passed after it.

Assumptions: schedule opt-in variables remain unset; this merge authority does not authorise deployments, worker dispatches or capture opening. No dependencies or secret-scan exceptions were added.


### Changes after review — merged-main integration

Merged predecessor histories forward and retained both sides of additive BUILD_ORDER conflicts. Remaining follow-ups are sequenced after the merged WP-3b package so current-head CI tests their combined content. The scoped owner merge exception is reflected consistently; deployment and photo-publication gates remain unchanged. Combined local verification: 98 workflow, coding-guidance, specification and app-build tests passed; Ruff and affected formatting passed. No dependency or secret-scan policy changed.

Assumption: each predecessor will merge before this PR is retargeted to main; no protection or production gate is bypassed.
