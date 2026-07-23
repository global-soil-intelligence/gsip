The library intake foundations now need the approved photo-privacy policy enforced before any media release. This specification defines private service-only screening authority, bounded jobs, personally authenticated human review and fresh authorization for the exact bytes exported. It splits implementation into WP-6fA database authority, WP-6fB detector/worker/review and WP-6fC export enforcement.

## Invariants

- I7/I11/I12: private media, screening evidence, operator identity and contributor context never enter public or agent surfaces; no new client-readable photo field or service credential in agent code.
- Capture/auth/publication remain closed. Calibration, model licensing, operator provisioning and each production action need separate owner evidence/go. A screen or human clearance cannot open the global publication gate.
- Every photo starts pending; permanent human withholding survives content/policy changes. Clearance is bound to actual sanitized bytes and the current approved policy. Existing QA/settlement, RLS, licences and late rights checks stay effective.
- Database authorization cannot atomically commit an external filesystem/Hub action; no immediate distributed-retraction claim.

## Verification and review

Specification-only change; pinned Prettier passed. Independent architecture review found no blocker in the private authority, rights/lock order, immutable evidence and export contract. The final wording/formatting delta is undergoing exact-head confirmation. Implementation tests and calibration are separate package requirements. No production or deployment action ran. Required exact-head CI is pending.

## Changes after review

- Preserve screened canonical bytes; a second JPEG encoding that changes SHA256 needs fresh screening. Synthetic compatibility audit found such changes in six of seven files.
- Keep withholding permanent for the opaque photo identity, with no v1 reversal API.
- Record bounded private card-mask evidence, without face/text boxes, OCR or crops.
- Distinguish token transport in a protected private RPC body from forbidden logging/URL/public exposure.
- Require fresh gate/byte authorization for same-date artifact reuse, and clarify the inherited implementation status.

## Assumptions and outstanding gates

The source objects are sanitized/oriented private JPEGs; workers independently verify them. Five claims/300-second leases are initial bounded behavior, not a throughput claim. Owner-admin configuration alone provisions operators or approves exact calibration/model/policy manifests. Candidate model compatibility is not privacy recall or deployment selection. No real contributor data is used. All further merges are currently held pending Justin's explicit decision about the one historical synthetic browser-fixture fingerprint documented on #51; no suppression has been added.

No dependencies, licence changes, production migration, worker dispatch, public photo release or capture opening.


### Final harness placement and current holds

CI ran the isolated browser harness: all 12 desktop browser checks now pass, including the public site's closed-capture label and launch-status link. Its processor-host audit then correctly flagged the test-only server when it lived under production scripts. The server now lives under test sources; the production-host audit remains unchanged. Local harness/processor regressions passed 14 tests and mypy passed 53 source files. The fixture placeholder cleanup and test-only move have been merged forward to this branch without rewriting history. Independent harness and specification reviews found no code/architecture blocker. Fresh complete CI remains required.

The current full-history gitleaks 8.21.2 finding is exactly `bb9bd8a583231ff63ec14a7622532ddb869d7cde:scripts/e2e_server.py:generic-api-key:32`, a historical noncredential browser placeholder. The current edited fixture scans clean. No ignore entry or scanner change has been applied; Justin's explicit approval for this single additional historical fingerprint is pending, so all further merges are held.

### Verified CI and remaining merge hold (2026-10-13)

At exact head `f1a644af2a78b1b9865385d603cb77ad156843eb`, [validate](https://github.com/global-soil-intelligence/gsip/actions/runs/38342978366) is successful. The full-history gitleaks checks remain failed solely for the historical synthetic browser-fixture fingerprint documented on #51; no additional suppression has been applied. This specification PR remains stacked on #51 and held for the same explicit owner exception. Code merging would not deploy models, approve calibration, provision operators or open photo publication.

## Changes after review — owner-approved exact historical fixture exception (2026-10-13)

Justin explicitly approved only the exact historical noncredential browser-fixture fingerprint `bb9bd8a583231ff63ec14a7622532ddb869d7cde:scripts/e2e_server.py:generic-api-key:32`. Commit `173e19363df60d029b2ffeb4a7df2e27d6ccd6b6` on the owning LIB-4C branch preserves the original four ignore lines and adds that single entry, with the approval recorded in AGENTS. It was merged forward through the ordered stack without force, rebase or history rewrite. The current test fixture was already cleaned forward; a new matching commit remains a failure. Detection rules, scanner configuration/workflow, redaction and history coverage are unchanged.

Before/after pinned gitleaks 8.21.2 whole-stack runs reproduced the exact one finding and then zero findings. The fresh scan after forward commits also reports zero. Independent narrow exception review passed (receipt SHA256 `258c1db45a803cfcac81b7234593df8a12f43f017496870f89e2d10f6ad23ef3`). Exact-head CI is being read back before merge; no previous-head pass is used as a new-head pass.

Assumptions: this approval covers only the named immutable fingerprint; every further suppression still requires explicit owner approval. No dependency/licence or runtime behavior change is introduced by this exception. Source merge authority does not authorize production deployments, worker dispatch, peer sharing or capture opening. Existing PR text is preserved.
