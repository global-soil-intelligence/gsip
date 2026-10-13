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

Choose an existing parent directory on encrypted private local storage, outside Git, public/shared folders and cloud backup. The CLI creates the final store directory with mode 700 and files with mode 600; it refuses public permissions and symlinked stores. The path above is a placeholder, not a directory created by GSIP. `inspect` reports counts only; validation failures never print incoming values. Re-importing an identical record is harmless; changing an existing measurement UUID fails. Changes need a new measurement UUID. Withdrawal removes that sample's stored records and preserves private sample and measurement tombstones, preventing re-import, including in a later process. A withdrawn measurement UUID cannot be reused under a different node/sample key; the markers retain only opaque identifiers and a withdrawal marker, never measurement content. A new measurement UUID cannot revive the withdrawn sample key. Withdrawal does not delete source files outside the store or revoke already produced datasets/models: operators must destroy those artifacts and rebuild eligible data. Back up only through your separately approved private retention process.

## Record meaning

The emitted JSON Schema is the authoritative version-1 exchange shape. IDs are opaque UUIDs: node, physical sample, measurement, grant, device/instrument, calibration, method and verifier. They are not geolocations or account credentials. Every measurement of one physical sample must share its sample key, context and grant. A node owner must resolve duplicate sample identities before import; cross-node deduplication/federation is not implemented.

`camera_rgb` contains three sRGB means and dispersions, surviving pixel count, sanitized-source hash, extractor version and card presence. It is **uncalibrated optical data**, never a measured spectrum. `instrument_reflectance` contains wavelength-resolved fractional reflectance and per-band uncertainties, source hash, instrument and calibration references. Version 1 rejects percent reflectance, absorbance, radiance, invented camera wavelengths, non-finite values, descending/repeated wavelengths and unknown fields. A spectrometer result outside [0,1] needs an explicitly reviewed adapter/protocol; this importer does not clip it.

Sample context records depth in cm and wet/moist/dry/unknown condition. Optional lab labels use GSIP canonical units with method, uncertainty and verifier references. Raw reports, precise points, timestamps, human names and instrument serials stay in your private evidence system, not this contract. The record's `consent_verified`, `pairing_verified`, `qa_status`, `synthetic`, `holdout` and `withdrawn` fields are local declarations. This CLI cannot verify their truth and does not grant canonical acceptance or publish anything. A declared instrument/calibration UUID is a reference, not proof of traceability.

## Joining the shared data chain

You can fork and extend the code, run a private local library node, and consume GSIP's public read API today. You cannot register that node to upload samples to GSIP using these commands. WP-LIB-4 schedules phone/private hosted intake and server verification; WP-LIB-5 schedules authenticated node exchange, physical-sample deduplication and rights propagation. Capture remains closed until the existing launch gates pass. Individual spectral publication remains blocked on the new fingerprinting/privacy review even if no coordinates are present.

No trained or independently validated soil reconstruction model is provided by the record store. Scientific training requires paired field measurements, verified calibration, rights eligibility and disjoint independent evaluation. Biological relationships need actual assays and an expert-reviewed vocabulary; no camera or spectral record here asserts microbial composition.
