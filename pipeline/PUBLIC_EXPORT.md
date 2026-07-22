# Nightly public export

`pipeline.export` selects only non-synthetic `qa_pass` submissions. It constructs every public row
from an allowlisted schema, scans for forbidden precise/private keys, requires the immutable grant,
downloads only canonical private photos, strips EXIF/XMP again, verifies the result, and writes a
Parquet dataset that is immediately round-tripped with `datasets.load_dataset()`.

Each dated build includes a manifest and a generated dataset card with separate ODbL 1.0 structured
data and CC BY-SA 4.0 photo notices, attribution, schema, and citation blocks. Re-running the same date
replaces that exact dated artifact, so rows and photo paths do not duplicate. The scheduled workflow
refreshes public H3 counts and publishes through Hugging Face Hub only when all server secrets exist.

Required deployment configuration:

- repository variable `HF_DATASET_REPO`
- repository secret `HF_TOKEN`
- repository secret `SUPABASE_SERVICE_ROLE_KEY`
