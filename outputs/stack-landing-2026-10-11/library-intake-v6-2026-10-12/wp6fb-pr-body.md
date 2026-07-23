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
