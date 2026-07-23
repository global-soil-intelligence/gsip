Add private server-side screening, durable worker receipts and a personally authenticated human review CLI for every published-photo candidate. Detector passes remain private dispositions, never publication permission. No worker, policy, reviewer credential, model selection, calibration approval or production publication is activated.

## Work package and invariants

WP-6fB, stacked on WP-6fA. Preserve I1–I15 and B1–B8: all-frame faces/text stay in scope, private image paths/detections/tokens never reach public output or logs, no proprietary detector/push service is introduced, and QA/settlement and launch gates remain unchanged. Every A/B/C photo follows the same path. Withhold only the flagged photo; eligible structured data remains independently releasable. No automatic blur.

Add exact-model/configuration binding, bounded subprocess inference, five-attempt/300-second SQL-lease operation, strict bounded transport, durable identical-request replay and a live server-derived operator review. The staged calibration harness always records publication_approved=false and null intervals for unknown coverage; it cannot grant policy approval.

## Acceptance and verification

- [x] Candidate models/configuration verified by exact bytes/digests before inference; actual sanitized digest registration before a fresh lease.
- [x] Whole-frame face and text screening. Optional card exception disabled pending independently verified complete-card localization.
- [x] Bounded worker/process cleanup, strict RPC/outbox requests, generic errors and no tokens passed to the detector/viewer or persisted in outboxes.
- [x] Explicit private human decision, permanent-withhold semantics and server-derived live operator identity; viewed bytes revalidated before intent/RPC.
- [ ] Independent final closure and exact-head CI appended when available.
- [ ] Full-history secrets check held on the inherited synthetic browser-harness fingerprint awaiting its separate explicit owner exception; no new suppression.

Corrected frozen preparation: 56 scoped tests, nine new independently reproduced fail-before cases, full Python 519 passed / four GDAL skips, Ruff and strict mypy ten authored modules/tests, formatting, and pinned gitleaks8.21.2 eleven-authored-file scan clean. Corrected real CPU compatibility smoke ran both exact pinned models on seven synthetic frames with zero card exclusions and verified a hard deadline with zero remaining child processes. This has no real face-positive/skin-tone/global-script/plate recall or approved calibration evidence. Host GDAL is absent; CI must run its required golden cases.

## Changes after review

- A bare marker or an occluded card could mask unrelated numerals in its guessed polygon. Disable the optional text mask entirely until complete-card localization is independently supported; keep faces and text across every pixel. Three new full/partial/bare-marker cases fail before the fix.
- A viewer edit/autosave, symlink or missing file could submit a decision against the earlier digest. Re-read with bounds/no-follow, verify metadata-free JPEG and original digest before durable intent or RPC; refuse generically. Six clear/withhold mutation cases fail before the fix.

## Dependencies, licences and assumptions

- No new installed package, service or SDK. Uses existing OpenCV4.14.0.94, NumPy2.4.6 and Pillow12.3.0.
- Benchmark candidates only: YuNet2023mar232,589 bytes, directory MIT; PP-OCRv3 English text detector2,423,490 bytes, directory Apache-2.0. Total2,656,079 bytes. Pinned upstream commit47534e27c9851bb1128ccc0102f1145e27f23f98; model digests and primary licence/maintenance links are in docs/PHOTO_PRIVACY_WORKER.md. Preserve upstream redistribution notices; weight directory licensing does not establish training-data provenance or owner/counsel approval.
- The pinned source is dated2026-05-28; face/text directory changes at that pin are2026-05-22/2024-11-06, maintenance signals only. Final Linux artifact size/transitive licences remain an activation gate. Existing Darwin audit measured127,473,296 library bytes and359,956,480 process peak RSS, not incremental/Linux model memory. Runtime includes Apache/MIT/LGPL/native notices and must not be called entirely MIT.
- Demo thresholds are compatibility parameters, not an approved high-recall operating point. Dedicated plate detection requires evidence of a material staged-evaluation gap and a properly licensed model.
- Private operator state needs encrypted, unshared local storage. Permission/path checks cannot certify every cloud provider or erase OS-viewer/backup caches; the tool removes its own copies only. Exact-byte checks do not attest what a human actually viewed.
- Actual SQL source/rights/lease authority belongs to WP-6fA and fresh export enforcement to WP-6fC. Production commands, model/policy calibration, operator provisioning and publication all need separate owner gates.
- All tests/images are synthetic; no private contributor data or secret was read, printed or committed. Project licences remain MIT/ODbL1.0/CC BY-SA4.0.

Codex authored implementation/fixes for Justin Hart. Independent code review is separate from an approving GitHub review or human DCO certification. No deployment, dispatch, merge bypass or capture opening.


### Changes after review — canonical JPEG byte boundary

Independent review confirmed the marker-mask and viewer-mutation fixes, then reproduced four unexamined byte channels accepted by the shared canonical JPEG guard: trailer plus another EOI, concatenated image, excess JFIF payload and a comment after scan data. A fifth JFXX-thumbnail case also fails before the fix. This draft remains held while the owning worker branch tightens complete-stream and APP0 validation and propagates the fix to the export branch. Existing scanner rules, metadata checks and all earlier regressions stay effective. No affected photo has been screened/published in production.

## Changes after review — final JPEG boundary closure (2026-10-13)

The owning worker branch now includes `b0f8e0f808629754bc6f4213f9c94e3149adfe55`. The shared QA metadata guard walks the entire JPEG stream through exact terminal EOI, requires the fixed canonical JFIF header, validates table/control fields and structural table generations/scan history, and refuses unused or overwritten definitions, unsupported metadata channels, duplicate/empty scans, trailers and concatenated streams. Existing sanitizer output bytes and unreadable-image behavior remain unchanged. Review counterexamples demonstrated the old guard could accept hidden payloads; tests fail against earlier guards. No scan rule, check, RLS, licence or publication gate was weakened.

The optional reference-card text exclusion remains disabled; the full frame is screened. The private viewed copy is rechecked after the human decision and before durable review/RPC. Those prior findings and the JPEG structural findings are independently closed at this exact commit.

Actual verification:

- Root Python: 682 passed, four host-GDAL skips. Ruff, formatting, mypy (64 source files), diff whitespace and pinned authored-file gitleaks checks passed.
- Independent frozen-source review: 234 scoped tests, 6,880 marker/field assertions and 47 full-decoder probes (46 refusals and one valid control) passed. Receipt SHA256 `9dafbdb2d0bab14972447c0fafa339429a8b852026c19109773a98a17c5bafd0` binds all 13 reviewed files to the commit.
- Synthetic CPU compatibility smoke: seven frames, hard-timeout cleanup with zero remaining children. This is not detector recall or face-positive calibration.
- Exact-head [CI validate](https://github.com/global-soil-intelligence/gsip/actions/runs/38354233257) passed: 686 Python with GDAL, 424 TypeScript, 593 database assertions, 45 populated migration assertions, six library and 31 photo two-connection cases, 12 browser tests and configured static/Deno/build checks.
- Full-history gitleaks 8.21.2 remains red on exactly the separately reported historical noncredential fixture fingerprint. The original three ignores are unchanged; further suppression still awaits explicit owner approval.

Assumptions/limits: this is structural marker/field/table-reference/scan-history validation, not proof that every Huffman entropy bit is consumed, a universal steganography defense, or trusted-producer attestation. QA reencoding remains in place. Real-data model calibration, exact deployment-runtime artifact/licence verification, policy/operator provisioning and all production/photo-publication gates remain held. No production deployment, worker dispatch or publication ran.

## Changes after review — owner-approved exact historical fixture exception (2026-10-13)

Justin explicitly approved only the exact historical noncredential browser-fixture fingerprint `bb9bd8a583231ff63ec14a7622532ddb869d7cde:scripts/e2e_server.py:generic-api-key:32`. Commit `173e19363df60d029b2ffeb4a7df2e27d6ccd6b6` on the owning LIB-4C branch preserves the original four ignore lines and adds that single entry, with the approval recorded in AGENTS. It was merged forward through the ordered stack without force, rebase or history rewrite. The current test fixture was already cleaned forward; a new matching commit remains a failure. Detection rules, scanner configuration/workflow, redaction and history coverage are unchanged.

Before/after pinned gitleaks 8.21.2 whole-stack runs reproduced the exact one finding and then zero findings. The fresh scan after forward commits also reports zero. Independent narrow exception review passed (receipt SHA256 `258c1db45a803cfcac81b7234593df8a12f43f017496870f89e2d10f6ad23ef3`). Exact-head CI is being read back before merge; no previous-head pass is used as a new-head pass.

Assumptions: this approval covers only the named immutable fingerprint; every further suppression still requires explicit owner approval. No dependency/licence or runtime behavior change is introduced by this exception. Source merge authority does not authorize production deployments, worker dispatch, peer sharing or capture opening. Existing PR text is preserved.
