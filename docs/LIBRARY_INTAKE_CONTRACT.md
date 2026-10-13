# Private library caller contract

WP-LIB-4A implements the separate `gsip-library-intake-v1` caller contract in
`@gsip/schema`. It prepares strict local validation only. It performs no network
request, verifies no evidence and activates no capture or hosted library service.
The hosted authority and phone integration are separate work packages under
[SPEC §16.5–16.8](SPEC.md#165-version-1-caller-contract-and-instrument-declaration-wp-lib-4a).

Use `parseInstrumentDeclaration(raw)` for an attached declaration JSON file and
`parseLibraryIntakeRequest(raw)` for the full caller envelope. Both reject input
above `MAX_LIBRARY_INTAKE_BYTES` (2,000,000 UTF-8 bytes) before parsing. A file picker
must check the file's byte size before reading it, then use the raw parser rather
than discarding extra fields from an ordinary local library record. Validate the
whole serialized envelope again before sending it. Duplicate decoded object keys,
including escaped aliases, are rejected; malformed inputs produce generic errors
without their contents or arbitrary field names.

The exported `InstrumentDeclarationSchema`, `LibraryIntakeRequestSchema`,
`LibraryIntakeReceiptSchema` and `LibraryIntakeCapabilitiesSchema` also validate
already-decoded values strictly, with generic errors. Already-decoded values cannot
establish whether the original JSON had duplicate keys or excessive whitespace.
UUIDs use 36-character `8-4-4-4-12` hexadecimal text, with no version/variant claim;
accepted uppercase text is normalized to lowercase. Digests must be lowercase.
Numbers are finite numbers, never coerced from strings or booleans. Context is
explicit, with `0 ≤ depth_top_cm < depth_bottom_cm ≤ 200` and one of `dry`, `moist`,
`wet` or `unknown`.

This **fictional declaration** illustrates the accepted attachment shape. Every
identifier and digest below is illustrative; no instrument source file or verified
measurement accompanies it.

```json
{
  "measurement_id": "00000000-0000-0000-0000-000000000001",
  "measurement": {
    "kind": "instrument_reflectance",
    "source_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
    "instrument_id": "00000000-0000-0000-0000-000000000006",
    "calibration_id": "00000000-0000-0000-0000-000000000007",
    "wavelength_nm": [450, 550, 650],
    "reflectance": [0.3, 0.4, 0.5],
    "uncertainty": [0.01, 0.01, 0.01]
  }
}
```

It may be placed in `instrument_declaration` in an envelope containing exactly
`schema_version`, `intake_id`, `node_id`, `sample_id`, `submission_id`,
`protocol_version`, `context` and `instrument_declaration`. Set the attachment to
`null` when none was supplied. The schema and protocol values are exactly
`gsip-library-intake-v1` and `gsip-capture-v1`. The server resolves the existing
finalized submission's shot B; a caller cannot supply a photo path, URL or photo ID.

Each declaration has 3–10,000 aligned bands, strictly increasing wavelengths from
200 to 25,000 nm, and reflectance and per-band uncertainty in `[0,1]`. Percent,
absorbance and radiance are unsupported. Instrument/calibration UUIDs and source
hashes remain unverified declarations. An ordinary `gsip-library-v1` record, PDF,
CSV, original instrument file or laboratory report is not this attachment format.
Grant, actor, consent, pairing, QA, synthetic, holdout, withdrawal, label and verifier
authority fields are rejected rather than copied or silently removed.

The safe receipt has only `intake_id` and `status`, which is
`stored_private_unverified` or `already_stored`. Capabilities have only `version`
and boolean `available`. Successful local validation or a future private receipt
does not establish permission, consent certification, physical pairing, calibration,
QA clearance, scientific validity or publication eligibility.

The fictional valid/invalid corpus in
`packages/schema/tests/fixtures/library-intake-conformance.json` exercises the
TypeScript raw parser and existing Python instrument validator with the same
measurement inputs. Field training, photo-publication, capture and production gates
remain separate and unchanged.
