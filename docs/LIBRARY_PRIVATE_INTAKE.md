# Private hosted intake v1

WP-LIB-4B adds the database half of the intake contract in `SPEC.md` §16.6–16.8. It stores a caller's declared sample context and optional instrument declaration privately. The only success states are `stored_private_unverified` and the equivalent retry state `already_stored`. Neither state grants scientific, training, export, QA, calibration, source-file, consent-verification, or physical-pairing eligibility.

## RPC contract

`library_intake_capabilities()` is available without an account and returns exactly `{version: "gsip-library-intake-v1", available: boolean}`. Availability requires both the existing capture gate and the separate library gate. The new gate defaults to false.

`record_library_intake(p_request jsonb)` is authenticated and accepts exactly:

```json
{
  "schema_version": "gsip-library-intake-v1",
  "intake_id": "00000000-0000-0000-0000-000000000001",
  "node_id": "00000000-0000-0000-0000-000000000002",
  "sample_id": "00000000-0000-0000-0000-000000000003",
  "submission_id": "00000000-0000-0000-0000-000000000004",
  "protocol_version": "gsip-capture-v1",
  "context": { "depth_top_cm": 0, "depth_bottom_cm": 20, "condition": "dry" },
  "instrument_declaration": null
}
```

The optional declaration replaces `null` with `{measurement_id: UUID, measurement: InstrumentReflectance}`. Instrument fields are exactly `kind`, `source_sha256`, `instrument_id`, `calibration_id`, `wavelength_nm`, `reflectance`, and `uncertainty`. Three through 10,000 aligned bands have strictly increasing wavelengths from 200 through 25,000 nm and fractional reflectance/uncertainty from zero through one. Depth values are JSON numbers with `0 <= top < bottom <= 200`; condition is `dry`, `moist`, `wet`, or `unknown`. Unknown fields and caller-supplied authority fail validation. UUID strings have the canonical 36-character hexadecimal syntax, accept any version/variant, and normalize case; source hashes require exactly 64 lowercase hexadecimal characters.

The response is exactly `{intake_id: UUID, status: "stored_private_unverified" | "already_stored"}`. `my_library_intake_receipt(p_intake_id uuid)` returns the same two-field receipt with `already_stored` for the current authenticated owner and live human actor. It reveals no private payload, grant, digest, restriction, or verification state. A lost write response can be recovered by retrying the same request. An equivalent retry is free; a changed identity/context/source relationship cannot overwrite the first claim.

Errors are `LI001` (activation hold), `LI002` (immutable identity/context conflict), `LI003` (100 new intakes per contributor per UTC day), `WD001` (withdrawn contribution or sample tombstone), `42501` (caller/source authorization refusal), and `22023` (invalid envelope). A closed gate holds writes, including already stored write retries. Owner receipt lookup is read-only and does not open the gate.

## Server authority and privacy

The server derives the contributor, active human actor, original contribution grant, finalized submission, and its owned shot-B photo. The photo path must match the authenticated user and submission in the existing private capture namespace. The grant must have the expected data/photo licenses and a terms version valid when accepted. An already admitted grant does not acquire the capture finalizer's freshness limit again. No caller grant, actor, ownership, timestamp, tier, location, storage path, URL, consent flag, QA flag, or holdout flag enters the envelope.

All ten new tables live in `private`, have RLS enabled with an explicit restrictive deny policy, and grant no direct table access to anonymous, authenticated, or service clients. Existing private-schema ACLs and public submission/photo RLS remain unchanged. Public entry points have an empty search path and definition-time-bound invoker bodies. Their narrowly granted private implementations derive `auth.uid()` themselves. The service role can call `set_library_intake_open(boolean)` but cannot directly rewrite the new tables. Deployment or setting this gate requires the separate existing production authorization; merging the package supplies no such authorization.

A server SHA-256 binds the exact normalized JSONB text persisted with the immutable payload. JSON number spelling and UUID case are semantically equivalent retries. This private digest proves those stored bytes only. No original instrument file is accepted or present, so source, calibration, and physical pairing remain false. Source hashes are pending caller claims. The same claimed hash cannot be reused for another sample by the same owner; a malicious matching hash cannot impose another owner's holdout or identity.

The server independently validates decoded JSONB shape, numeric bounds, aligned arrays, and a two-million-byte bound on normalized UTF-8 JSONB text. PostgreSQL has already collapsed duplicate keys and discarded raw whitespace/escape spelling by this boundary. The raw shared client parser must enforce original UTF-8 size and reject literal or escaped duplicate keys before JSONB submission. Database tests explicitly demonstrate that normalization limit. Server canonical size can be larger than a compact valid client envelope, so callers must handle a validation refusal without silently altering declarations.

## Withdrawal and monotonic restrictions

Intake, deletion-request filing, and grant withdrawal serialize on the contributor row. An additive grant-withdrawal trigger first creates opaque sample refusal tombstones, then deletes the sample and all linked intake/declaration/restriction payloads in the same transaction. Filing an account deletion also removes private namespace ownership and quota counters, while retaining only retired node UUIDs so a new owner cannot reuse an erased namespace with a fresh sample. Contribution withdrawal retains the current namespace binding so its owner can use a later grant for a new sample. Sample tombstones cannot be resurrected under a later grant. Erased intake and measurement UUIDs remain in an opaque retirement ledger with no payload or contributor reference; no later grant or different owner can reuse those declaration identities. Quota counters survive contribution withdrawal.

The existing deletion-worker apply and completion signatures and bodies are unchanged. An added completion guard refuses completion while covered library samples remain. This protects against an old worker claiming success after deleting only the original tables. Source submission/photo deletion also writes refusal tombstones before erasure. It does not take the contributor lock after taking a source row lock: the existing source/FK locks serialize direct deletion against intake without reversing rights lock order.

Existing source holdout/synthetic flags initialize sample-wide restrictions. Later holdout and synthetic updates propagate to the linked sample and can only turn restrictions on. Unsealing or deleting a label cannot remove the private seal. Intake does not lock a parent submission `FOR UPDATE`; its source FK key-share locks remain compatible with holdout inserts and synthetic updates. These flags remain private and convey no v1 eligibility. Claims with different unknown sample IDs cannot establish that two physical samples are the same.

## Compatibility and local verification

The migration is additive, creates no accepted backfill, and defaults unavailable. Older deployed schemas remain usable by the legacy capture path. The optional phone workflow must hold its library queue record when the capability is missing, has an unknown version, or is unavailable, before creating an account or submission for that record. Activation requires reviewed migrations, app compatibility and schema-cache/RPC checks, green CI, and separate deployment/capture authorization.

The new pgTAP suites cover caller roles, private ACL/RLS, strict validation, immutable retries, ownership/source binding, quota, unverified declarations, monotonic restrictions, account deletion, namespace retirement, tombstones, and old-worker compatibility. The migration regression fixture compares legacy row counts, existing gate values, existing RPC definitions, and existing ACL/RLS across the additive migration. The conformance SQL mirrors the shared synthetic instrument corpus from WP-LIB-4A, including the JSONB duplicate-key limitation.

For actual two-connection local races, run the standard-library script only against a disposable `gsip_lib4b_*` database in the local `supabase_db_gsip` container:

```sh
python3 scripts/test-library-intake-concurrency.py --database gsip_lib4b_example
```

The existing migration-test runner executes these races in its independent disposable cluster during CI using `--native-psql`. An independent Unix-socket-only cluster inside that container can be selected with `--socket /tmp/gsip_lib4b_example --port 55494`. The script uses synthetic UUIDs and context, opens gates only in the explicit disposable target, and checks both orderings of intake versus withdrawal, source deletion, and holdout insertion. It requires no production credential and emits only generic counts and pass/fail receipts. This is local database evidence; it does not establish deployed migration state, real capture readiness, scientific verification, or useful adoption.
