# Nightly public export

`pipeline.export` selects only non-synthetic `qa_pass` submissions and, within them, only photos
whose own QA verdict is `pass`. It constructs every public row from an allowlisted schema, scans for
forbidden precise or private keys (including the raw `h3_r8` and `h3_r6` cells), requires the
immutable grant, downloads only canonical private photos, strips metadata again, verifies the
result, and writes a Parquet dataset that is immediately round-tripped with `datasets.load_dataset()`.

## Withdrawals and attribution (WP-6d)

- A submission whose grant has a `grant_withdrawals` row never becomes a candidate: it is neither
  released, set aside nor counted. A contributor's request withdraws their grants the moment it is
  made, and the hourly rights worker deletes the rows soon after.
- Withdrawals are read when the export starts and again just before publishing
  (`honour_late_withdrawals`). If any grant in the build was withdrawn in between, the export rebuilds
  once without those observations; if more arrive during the rebuild, it refuses to publish. A
  release built after a request therefore never contains the withdrawn observations.
- Photos publish only under the default pseudonym, or under a typed attribution name that a steward
  approved for that contributor (`attribution_reviews`). A pending or rejected name releases the row
  without photos, so the name appears nowhere; such photos are never read from Storage. Review names
  with `uv run python -m pipeline.attribution_review list|approve|reject`.

## k-anonymous locations (SPEC I7)

Rows carry `h3_cell` and `h3_resolution` instead of the private cells. Each observation is placed in
the finest cell among resolutions 8, 6 and 4 whose assigned observations come from at least 3
distinct contributors (`pipeline/k_anonymity.py`). Groups form bottom-up from observations not
already placed at a finer resolution, so no published cell's own members span fewer than 3
contributors. Observations that qualify at no resolution are withheld until they do; the dataset
card reports how many. The public `h3_cells` table receives exactly these cells, and the database
refuses any cell below k = 3.

## What a row never carries

No precise geometry, raw `h3_r8`/`h3_r6` cell, GPS accuracy, contributor or grant identifier,
device model or private camera metadata. Two less obvious exclusions follow from SPEC I7 ("by value
as well as by name"): **point-level priors** (eight SoilGrids properties matched against the public
rasters pinpoint a 250 m pixel, finer than any published cell) and the **GPS plausibility score**
(it encodes the private GPS accuracy; the check is released as pass or fail only).

## Failures

Before reading a photo, the export re-derives its owner path from database facts; a mismatch is a
privacy failure. A row that cannot be released this time is set aside and the release continues:
a missing photo object (HTTP 400 or 404), an unreadable photo, a missing grant, an invalid cell, or
a `qa_pass` status without passing shots A and B (a pre-v3 artifact). k-anonymity is computed after
set-asides, so a set-aside row can never leave a published cell below k.

The whole release aborts, publishing nothing, on:

- a privacy assertion: metadata in a canonical photo or surviving sanitization, a forbidden field
  in a row, or a photo path that does not match its owner;
- an infrastructure error: any other Storage or database failure (5xx, 429, timeouts), so an
  outage can never publish a hollowed-out release that wipes the dataset and the map;
- widespread set-asides: more than 3 rows or 10 % of candidates, whichever is larger.

Set-aside and withheld submission IDs are written to a private report beside the release folder
(`output/export/<date>.report.json`), never uploaded. The workflow log prints counts only, because
logs of a public repository are public.

Each dated build includes a manifest and a generated dataset card with separate ODbL 1.0 structured
data and CC BY-SA 4.0 photo notices, attribution (marked as untrusted text), schema, per-photo QA
checks, a note on how to sample priors for a published cell, and citation blocks. Capture timestamps are date-truncated. Empty nights produce an explicit
valid snapshot instead of an alarm. Re-running the same date replaces that exact dated artifact. The
scheduled workflow deletes stale Hub photo/data paths, publishes through Hugging Face Hub, and only
then replaces the public cells through a service-role-only transaction.

Hub deletion removes files from the current branch head, not Git history. A verified privacy takedown
also requires the repository owner to squash or delete the affected Hub history before declaring
erasure complete.

Required deployment configuration:

- repository variable `SUPABASE_URL`
- repository variable `HF_DATASET_REPO`
- repository secret `HF_TOKEN`
- repository secret `SUPABASE_SERVICE_ROLE_KEY`
