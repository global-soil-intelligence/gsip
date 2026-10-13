# Open soil spectral library: developer entry point

GSIP's primary goal is an open soil spectral reference library. Smartphones collect guided images and context and link physical samples to instrument/lab evidence. Maps and AI models use that evidence. The v5 architecture is proposed in [SPEC §16](SPEC.md#16-open-soil-spectral-library-v5); these private local tools are preparation, not a production deployment or a public dataset.

## What you can run now

Use the pinned Python environment (`uv sync --frozen --all-groups`). No extra dependency, account, secret, service-role key or network is needed by the library CLI itself. It runs on macOS/Linux, using filesystem locking. Windows is not supported by this first store implementation.

```sh
uv run python -m pipeline.library schema
uv run python -m pipeline.library --store /private/local/soil-library import /private/local/measurement.json
uv run python -m pipeline.library --store /private/local/soil-library inspect
uv run python -m pipeline.library --store /private/local/soil-library withdraw --node <node-uuid> --sample <sample-uuid>
```

Choose an existing parent directory on encrypted private local storage, outside Git, public/shared folders and cloud backup. The CLI creates the final store directory with mode 700 and files with mode 600; it refuses public permissions and symlinked stores. The path above is a placeholder, not a directory created by GSIP. `inspect` reports counts only; validation failures never print incoming values. Re-importing an identical record is harmless; changing an existing measurement UUID fails. Changes need a new measurement UUID. Withdrawal removes that sample's stored records and preserves a tombstone, preventing re-import, including in a later process. It does not delete source files outside the store or revoke already produced datasets/models: operators must destroy those artifacts and rebuild eligible data. Back up only through your separately approved private retention process.

## Record meaning

The emitted JSON Schema is the authoritative version-1 exchange shape. IDs are opaque UUIDs: node, physical sample, measurement, grant, device/instrument, calibration, method and verifier. They are not geolocations or account credentials. Every measurement of one physical sample must share its sample key, context and grant. A node owner must resolve duplicate sample identities before import; cross-node deduplication/federation is not implemented.

`camera_rgb` contains three sRGB means and dispersions, surviving pixel count, sanitized-source hash, extractor version and card presence. It is **uncalibrated optical data**, never a measured spectrum. `instrument_reflectance` contains wavelength-resolved fractional reflectance and per-band uncertainties, source hash, instrument and calibration references. Version 1 rejects percent reflectance, absorbance, radiance, invented camera wavelengths, non-finite values, descending/repeated wavelengths and unknown fields. A spectrometer result outside [0,1] needs an explicitly reviewed adapter/protocol; this importer does not clip it.

Sample context records depth in cm and wet/moist/dry/unknown condition. Optional lab labels use GSIP canonical units with method, uncertainty and verifier references. Raw reports, precise points, timestamps, human names and instrument serials stay in your private evidence system, not this contract. The record's `consent_verified`, `pairing_verified`, `qa_status`, `synthetic`, `holdout` and `withdrawn` fields are local declarations. This CLI cannot verify their truth and does not grant canonical acceptance or publish anything. A declared instrument/calibration UUID is a reference, not proof of traceability.

## Joining the shared data chain

You can fork and extend the code, run a private local library node, and consume GSIP's public read API today. You cannot register that node to upload samples to GSIP using these commands. WP-LIB-4 schedules phone/private hosted intake and server verification; WP-LIB-5 schedules authenticated node exchange, physical-sample deduplication and rights propagation. Capture remains closed until the existing launch gates pass. Individual spectral publication remains blocked on the new fingerprinting/privacy review even if no coordinates are present.

No trained or independently validated soil reconstruction model is provided by the record store. Scientific training requires paired field measurements, verified calibration, rights eligibility and disjoint independent evaluation. Biological relationships need actual assays and an expert-reviewed vocabulary; no camera or spectral record here asserts microbial composition.

## Extracting optical measurements from a phone photo

WP-LIB-2 supplies an offline staged-only extractor:

```sh
uv run python -m pipeline.phone_optics --store /private/local/soil-library --template /private/local/camera-record.json --image /private/local/staged-photo.jpg
```

The template is a valid `camera_rgb` record with new measurement identity and `synthetic: true`. The extractor replaces only its measurement payload. It sanitizes and orients pixels, converts embedded profiles to sRGB, masks the detected reference card with the existing margin, then measures RGB means and standard deviations in the remaining candidate soil pixels. It keeps a sanitized-content hash, not raw metadata, and does not advance consent, pairing or QA states. All measurements stay uncalibrated, including images with a detected card. Without a card the candidate region is the whole frame; actual soil segmentation remains a future QA improvement. Insufficient candidate pixels fail. Real contributor imagery is refused by this record-producing CLI until WP-6f/hosted verification is integrated; synthetic staged images exercise the software without claiming field evidence.

## Run the complete local demo

```sh
uv run python -m pipeline.library_demo --output /private/local/new-demo-directory
uv run python -m ml.library_baseline --store /private/local/new-demo-directory/records --output /private/local/another-new-baseline --demo
```

The first command creates 12 fictional physical samples: staged phone images go through the real optical extractor, and invented reflectance values form a deliberately simple paired reference. It imports 24 private records and fits a linear RGB-to-reflectance baseline. All records and outputs are explicitly synthetic. The demo's reconstruction error is a software check, **not a sensor benchmark or soil result**. It needs no paid service, new dependency, training download or production credential.

The baseline requires matching sample context and grant, verified local pairing/consent declarations, passing QA and one camera/instrument pair per sample. It excludes whole samples if any record is withdrawn, held out or ineligible; synthetic records cannot enter field preparation. Ambiguous repeated measurements, conflicting identities, mixed grids/devices and source files shared across different sample identities are refused. Bulk instrument files need a separately specified adapter with per-measurement source identity. Sample-hashed partitions separate training from development; sealed holdouts are never used. Development partition error does not substitute for independent spatial/device evaluation.

Outputs are private `model.json`, `partitions.json` and `receipt.json`, created in a new directory without overwriting older evidence. The receipt is written last; a directory without it is incomplete. It records input digest, algorithm/NumPy versions, partition counts and development error. Coefficients and sample keys remain private. This model has no calibrated intervals and is marked ineligible for deployment; it predicts reflectance in a fictional demo, never soil chemistry or biology. Field model training is deliberately blocked until canonical rights/provenance and photo-screening verification are integrated. The demo is deterministic for the same inputs and locked environment; hashes and NumPy versions permit checking platform differences rather than claiming universal byte-identical floating-point results.
