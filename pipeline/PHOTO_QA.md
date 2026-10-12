# Private photo QA

The deterministic gate (`deterministic-v2`) runs entirely on private objects. New `photos` rows
enqueue durable `qa_jobs` rows. Before touching Storage, the worker re-derives the only path a photo
may name, `{auth_uid}/{submission_id}/{shot_type}/{uuid}.jpg`, from database facts (the
submission's contributor and the photo's shot). A mismatch dead-letters the job with
`storage_path_mismatch` and makes no Storage request; the database enforces the same binding on
insert and update for every role (WP-6b).

The worker downloads the `incoming-photos` object, applies the EXIF orientation, converts any
embedded colour profile (Display P3, for example) to sRGB, and only then strips EXIF, XMP, ICC,
comments and every non-JFIF APP segment by re-encoding. It keeps the schema allowlist of non-location
camera fields plus a colour-space class (`srgb`, `display_p3`, `other`, `none`), verifies the
sanitized bytes with an independent marker scan, and promotes them to `submission-photos`.

Checks run on the soil, not the card. When the ArUco marker is found, the card's outline is projected
from the marker homography, enlarged by 12 % and masked out:

| Check              | Rule                                                                     | Failure routes to |
| ------------------ | ------------------------------------------------------------------------ | ----------------- |
| `soil_region`      | at least 20 % of the frame remains as soil                               | fail              |
| `sharpness`        | Laplacian variance on the eroded soil mask ≥ 55                          | fail              |
| `exposure`         | clipped and mid-tone limits on soil pixels                               | fail              |
| `card_detection`   | marker and patches recovered (records calibration; never fails)          | —                 |
| `gps_plausibility` | accuracy ≤ 250 m and no gross prior mismatch; missing accuracy = unknown | review (flagged)  |
| `duplicate`        | 64-bit perceptual hash of the largest soil band beside the card          | review (flagged)  |

Each photo receives a verdict in `photos.qa_status` (`pass`, `fail`, `flagged`, or `error` when the
job dead-letters). The worker never writes a submission's status: once the owner has finalized
the submission with shots A and B, `settle_submission()` derives it from those two shots (SPEC
section 5). A failed optional shot C is simply left out of releases. Each run also settles finalized
submissions whose photos finished QA before finalize arrived.

Thresholds are provisional until the 50-photo field pilot calibrates them. Card-less photos remain
eligible and are explicitly `uncalibrated`. A Phase 2 soil classifier can implement the
`SoilClassifier` protocol without changing the ingest contract.

Successful promotion, database recording, settlement and quarantine deletion are one retryable
workflow. A failed sanitizer never promotes an object. Decoder errors and decompression bombs
dead-letter after four attempts without leaving a job in `processing`; stale processing jobs are
requeued after 15 minutes. Quarantine cleanup runs hourly on its own schedule
(`quarantine-cleanup.yml`, `python -m pipeline.qa_worker --cleanup-only`) and also after each QA run;
it walks the full owner/submission/shot path recursively and deletes raw objects older than 24 hours.

Because the hosted database tier does not provide h3-pg, authenticated client H3 hints are cleared by
the insert trigger, and this service-role worker derives H3-r8 and H3-r6 from the private PostGIS
geometry. Duplicate comparison excludes sibling photos from the same submission and paginates beyond
PostgREST's row cap.
