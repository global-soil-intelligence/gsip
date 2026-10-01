# Nightly public export

`pipeline.export` selects only non-synthetic `qa_pass` submissions. It constructs every public row
from an allowlisted schema, scans for forbidden precise/private keys, requires the immutable grant,
downloads only canonical private photos, rejects any dirty canonical source, strips metadata again,
verifies the result, and writes a
Parquet dataset that is immediately round-tripped with `datasets.load_dataset()`.

Each dated build includes a manifest and a generated dataset card with separate ODbL 1.0 structured
data and CC BY-SA 4.0 photo notices, attribution, schema, and citation blocks. Capture timestamps are
date-truncated. Empty nights produce an explicit valid snapshot instead of an alarm. Re-running the
same date replaces that exact dated artifact, so rows and photo paths do not duplicate. The scheduled
workflow deletes stale Hub photo/data paths, publishes atomically through Hugging Face Hub, and only
then replaces public H3 counts through a service-role-only transaction.

Hub deletion removes files from the current branch head, not Git history. A verified privacy takedown
also requires the repository owner to squash or delete the affected Hub history before declaring
erasure complete.

Required deployment configuration:

- repository variable `HF_DATASET_REPO`
- repository secret `HF_TOKEN`
- repository secret `SUPABASE_SERVICE_ROLE_KEY`
