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
failed sanitizer never promotes an object. The sanitizer removes EXIF (including GPS/SubIFD), XMP,
ICC, JPEG COM comments, and every non-JFIF APP segment, then verifies the encoded bytes with an
independent marker scan. Decoder errors and decompression bombs dead-letter without leaving a job in
`processing`; stale processing jobs are requeued after 15 minutes. Quarantine cleanup walks the full
owner/submission/shot path recursively and deletes raw objects older than 24 hours.

Because the hosted database tier does not provide h3-pg, authenticated client H3 hints are cleared by
the insert trigger. Before a submission can become `qa_pass`, this service-role worker derives H3-r8
and H3-r6 from the private PostGIS geometry and writes the cells in the same status update. Duplicate
comparison excludes sibling photos from the same submission and paginates beyond PostgREST's row cap.
CI fixtures cover sharp, blurry, card-less, card-present, GPS-implausible, duplicate, metadata-channel,
hostile-decoder, stale-queue, recursive-cleanup, and pagination paths.
