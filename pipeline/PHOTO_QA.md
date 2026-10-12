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

## Capture evidence and provenance tiers (WP-6e)

Before sanitizing, the worker reads the original upload's capture metadata and compares it with
the observation (`pipeline/provenance.py`). It stores only `photos.capture_evidence_private`:
whether an EXIF capture time is present and absolute (it carries its time zone, or is the GPS fix
time), its difference in seconds from the claimed capture time, its age in seconds when the person
accepted the terms for the observation (the grant's acceptance time, which the server bounds to the
30 days before it received the grant), whether an EXIF position is present, and its distance in
metres from the claimed point. Never coordinates or timestamps: the database refuses any other key,
any fractional number and any other type (I7).

The worker never writes a tier. The database derives each photo's tier from its evidence
(`private.photo_tier_from_evidence`): tier 1 when the absolute capture time lies within 30 minutes
of the claim and within the hour before the acceptance (five minutes of clock skew allowed), and any
EXIF position lies within 250 m of the claimed point; otherwise 0, and always -1 for a synthetic
submission. A submission's tier is the lower of shots A and B. A direct write to either tier is
ignored. The acceptance anchor matters: a year-old gallery photo agrees with a capture time taken
from its own file, but not with an acceptance a year later; likewise an observation whose terms
were accepted again after waiting more than 30 days stays at tier 0. Unreadable or hostile metadata is no
evidence (tier 0), never a QA failure. The client's claims (`ingest_path`, `capture_method`,
`location_source`, `client_version`) are not even read here: they never raise a tier (I10).
Capture metadata can be forged, so tier 1 means corroborated, not proven; attestation (tier 2) and
laboratory pairing (tier 3) are reserved.

## Checks

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
