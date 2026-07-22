# Private photo QA

The non-ML gate runs entirely on private objects. New `photos` rows enqueue durable `qa_jobs` rows.
The worker downloads the corresponding `incoming-photos` object, strips EXIF and XMP by decoding and
re-encoding it, retains only the schema allowlist of non-location camera fields, and verifies the
sanitized bytes before promotion to `submission-photos`.

Checks are deterministic: Laplacian sharpness, clipped-pixel exposure, ArUco/card-patch recovery,
location-accuracy and gross prior plausibility, and 64-bit perceptual-hash distance. Card-less photos
remain eligible and are explicitly `uncalibrated`. A Phase 2 soil classifier can implement the
`SoilClassifier` protocol without changing the ingest contract.

Successful promotion, database recording, and quarantine deletion are one retryable workflow. A
failed sanitizer never promotes an object. The worker also deletes raw quarantine objects older than
24 hours. CI fixtures cover sharp, blurry, card-less, card-present, GPS-implausible, and duplicate
paths, plus identical-run determinism and metadata removal.
