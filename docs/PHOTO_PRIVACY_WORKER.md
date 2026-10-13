# Private photo screening preparation (WP-6fB)

This package implements the private worker/operator portion of SPEC §15.5–15.9.
It activates no worker, hosted policy, capture, reviewer credential or publication
gate. Photo QA and submission settlement are unchanged. An individual detector
pass or false-positive review is a private disposition, never publication authority.
WP-6fA owns SQL/RLS/rights enforcement; WP-6fC owns release enforcement. All three
packages, owner-approved calibration and a separate production go remain required.

## Pinned benchmark candidates

No model is selected for deployment. Both files are verified by exact byte count
and SHA-256 before OpenCV consumes the same immutable in-memory bytes. Files are
supplied in a private operator-controlled model directory; there is no automatic
download, model replacement, quantized alternative or new package dependency.

| Artifact                                 |     Bytes | SHA-256                                                            | Directory license |
| ---------------------------------------- | --------: | ------------------------------------------------------------------ | ----------------- |
| `face_detection_yunet_2023mar.onnx`      |   232,589 | `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` | MIT               |
| `text_detection_en_ppocrv3_2023may.onnx` | 2,423,490 | `03f550c6b406fda8bf54bd8327815f6c7e2edd98cea02348c93d879254366587` | Apache-2.0        |

Source commit: `47534e27c9851bb1128ccc0102f1145e27f23f98`. The primary
[YuNet README/license](https://github.com/opencv/opencv_zoo/tree/47534e27c9851bb1128ccc0102f1145e27f23f98/models/face_detection_yunet)
and [PP-OCR README/license](https://github.com/opencv/opencv_zoo/tree/47534e27c9851bb1128ccc0102f1145e27f23f98/models/text_detection_ppocr)
explicitly license all files in those directories, including the weights. Preserve
their copyright/license notices when distributing the artifacts. Code licenses
alone do not establish training-data provenance or global detector performance.
The pinned snapshot is dated 2026-05-28; latest directory changes at that pin are
2026-05-22 and 2024-11-06 respectively. These are maintenance signals, not a support
promise. The newer YuNet 2026may model targets a different runtime engine and is
not substituted. A dedicated plate detector remains outside this package.

The existing locked OpenCV distribution is `opencv-contrib-python-headless`
4.14.0.94 / OpenCV 4.14.0, with NumPy 2.4.6 and Pillow 12.3.0. Both candidate models
load and infer on its CPU backend. Combined weights add 2,656,079 bytes; no Python
or service dependency is added. The preparation audit on Darwin arm64 measured
127,473,296 bytes of existing native libraries and a peak process RSS of
359,956,480 bytes for its synthetic compatibility run. That RSS includes Python,
libraries, models, fixture arrays and warm-up; it is not isolated model memory.
The final Linux worker image, transitive libraries and runtime size remain to be
audited. Core OpenCV is Apache-2.0, packaging has an MIT notice, and bundled native
notices also include LGPL-2.1 FFmpeg/macOS codec libraries and permissive components.
The entire runtime must not be described as MIT. Preserve the bundled notices and
applicable redistribution obligations in any separately authorized worker artifact.

## Full-frame screening and exact receipts

`pipeline.photo_privacy` validates the publish-ready JPEG, refuses embedded
metadata/trailing bytes, and preserves its exact bytes. Both original resolution
and half resolution use overlapping 640-pixel tiles with 128-pixel overlap; edge
tiles cover the final row/column. Face and scene-text inputs include every pixel, including the reference card.
The existing single-marker homography cannot establish that a complete, unobscured
GSIP card occupies its projected polygon. A bare marker or occluded card could hide
unrelated text there. The optional SPEC exception therefore stays disabled until
independent complete-card verification exists and is reviewed. No soil mask,
arbitrary context/face exclusion, OCR-recognition clearance or automatic blur exists.

Receipts currently carry `card_exclusion=null`; the benchmark configuration pins
`full-frame-no-exclusion-v1`. The strict contract retains exact dimensions, mask
hash, pixel count and 1.12 margin for a future separately reviewed implementation;
no current operation emits an exclusion mask. Previous preparation compatibility
runs used the provisional marker mask and do not validate this corrected behavior.
Detailed detections, image crops and recognized strings are never persisted or
printed. Non-finite/out-of-frame output, candidate saturation, unsupported images,
missing/mismatched models and exhausted view/time budgets cannot produce a pass.
Counts are candidate outputs across overlapping views, not unique people or objects.

The immutable configuration pins adapter, card geometry/design, JPEG validation
and receipt-contract source bytes, exact model hashes, runtime versions,
preprocessing, thresholds, tile/scale policy and margin. Its exact file
digest and the exact calibration-manifest digest must match the service-issued
lease. The demo thresholds are benchmark parameters, not approved high-recall
thresholds. Native inference runs in a spawned process with the current lease/time
budget; timeout terminates/kills/joins the child. No service/reviewer credential is
passed to the detector or local image viewer. Process-start/cleanup overhead and target memory costs
still require deployment measurement; the SQL lease bounds remain authoritative.

## Worker and human operation

The worker uses only the nine narrowly defined service RPCs and the existing
private sanitized-photo bucket. It probes private capabilities; no active policy
means no claim or image download. A configured benchmark policy can screen while
publication remains closed. Unknown/changed actual bytes are registered with an
expected revision, invalidating the old lease. A fresh lease is required before
screening/completion. Legacy photos and A/B/C shots follow the same path.

The worker persists a strict receipt/lease outbox in a protected local directory
before completion. Lost responses replay the same request UUID and exact bytes,
including after restart. Stale/withdrawn responses cannot resurrect state;
immutable conflicts remain held. SQL owns five claims per generation, 300-second
leases and scheduled backoff. Each client run is bounded and never sleeps in an
unbounded retry loop. No worker operation writes QA status or settles a submission.

The private review CLI requires service credentials plus `GSIP_PHOTO_REVIEW_TOKEN`
from environment or an approved secret store. The personal token is exactly 64
lowercase hex characters representing 32 random bytes. It is never a CLI argument,
filename, URL, outbox value or log. SQL hashes it and derives a live allowlisted
operator; no caller reviewer ID is accepted. Only owner-admin provisioning can
create/revoke that mapping. Worker/export credentials cannot provision reviewers,
select/approve policy or open publication.

An operator context authorizes a private download. The CLI checks its exact hash,
saves a mode-600 temporary JPEG under a mode-700 directory, opens a fixed local
viewer and waits for an explicit human decision. Before a clear/withhold intent is
persisted or submitted, a bounded no-follow read revalidates the viewing copy's
metadata-free JPEG and exact original digest. Changed, linked or missing copies
are refused; this does not attest what a human actually saw. Copies are removed on decision,
abort or failure. Clear is limited to supported current false positives; pending,
erroring/unsupported or permanently withheld content cannot be cleared. Privacy-risk
withholding is permanent for that opaque photo identity, across content/policy
generations. A durable review outbox preserves the original review UUID for lost
responses without retaining the token or image. Local storage must be encrypted,
outside Git and shared/cloud folders; the tools refuse unsafe permissions, symlinked
roots and common shared/cloud paths. They cannot certify every provider's storage
configuration or erase copies cached elsewhere by an operator/viewer/backup system.

CLI errors and HTTP failures print only generic classes/counts. Parsers never echo
invalid private arguments. HTTP responses/images are streamed with byte bounds;
redirects and default ambient proxies are disabled. Tokens appear only in TLS
POST bodies, service credentials only in authorization headers. No runtime image
is sent to an external detector service or agent-facing interface.

## Private calibration harness and remaining evidence

`pipeline.photo_privacy_calibrate` evaluates a strict staged manifest in private
storage and writes a new private evidence directory. An empty manifest emits
explicit unknown coverage without loading weights. Each unique sanitized-content
hash counts once; duplicate frames/retries cannot inflate category samples.
Reports contain category positive/negative counts, supported negative denominators,
misses, false positives, unsupported/error counts, Wilson 95% intervals, declared
strata and measured runtime. Zero denominators have null intervals. Detailed paths,
images, boxes, OCR text and reviewer tokens are absent from reports/stdout.

These metrics describe component candidate outcomes per declared staged frame,
not localized instance recall or independently verified ground truth. Plate/house
number/numeral categories use scene-text detection, not a plate classifier or OCR.
Material/labels are declarations. The harness always records
`publication_approved=false`, has no approval/provisioning/gate RPC, and cannot
turn a benchmark into owner approval. Missing category coverage remains unknown.
No preparation run supplies real face-positive, skin-tone, global script/plate
coverage or GSIP-calibrated recall. Permissioned category evaluation, confidence
assessment, target artifact audit, independent implementation review/CI, operator
provisioning and exact-target production go remain separate gates.

The existing export's second JPEG encoding can change already-sanitized hashes
(six of seven private synthetic preparation scenes did). WP-6fC must preserve
the exact screened canonical bytes and obtain fresh final authorization. Changed
bytes, policies, human restrictions or rights cannot reuse earlier clearance.
Structured eligible observations remain releasable with empty photo lists while
photo publication is closed or a photo is withheld.
