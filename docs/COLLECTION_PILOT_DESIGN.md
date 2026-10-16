# Invited phone-browser pilot: implementation contract

**SPEC v15 / WP-COLLECT-2 #82 — source implementation authorized 2026-10-16; no production authority.**

Justin authorized #79/#81 ordered merges and #82 for an invited phone-browser pilot. This
contract precedes source implementation. No account, membership, database, worker, setting,
release or deployment operation is authorized. Capture and hosted library intake remain closed.
The invited adult audience and owner-provisioned accounts are selected. Actual enrollment,
duration/capacity, effective contributor notices and bounded exceptions to public-launch gates
remain separate owner operations/decisions. No additional dependency or service is selected.

## Server admission and immutable classification

An additive migration introduces a private invitation allowlist keyed by `auth.users.id`, with
revocation. Clients cannot list, enroll or edit members. No provisioning RPC or automatic invite
backfill exists. Admission requires an existing non-anonymous auth user, current unrevoked
membership and both existing capture/library gates. Do not weaken existing ownership, terms,
quota, rights, actor, holdout, provenance or Storage predicates.

Public `collection_pilot_capabilities()` returns exactly:

```json
{
  "version": "gsip-invited-pilot-v1",
  "mode": "invited_private",
  "member": false,
  "capture_open": false,
  "library_intake_available": false,
  "publication_held": true
}
```

The booleans are computed from the requesting identity and current gates; no member identity
or list is exposed. Missing/old/unknown capabilities hold before writes. Restrictive policies
cover contributor/grant/submission/photo/incoming-Storage writes, and privileged finalization
and library ingest perform the same check. Rights requests and existing-owner private reads do
not require an active invitation or open capture. Service cleanup/QA/rights can continue while
intake is closed. No service-role session is added to a browser or agent API.

Every new submission receives a server-owned `collection_scope = private_pilot`, including
ordinary observations without optional library context and service-origin rows. Existing rows
are backfilled as `legacy` without changing their rights or provenance. Clients cannot choose
or alter scope; updates cannot promote a pilot row, including with service-role privileges.
Pilot scope is distinct from QA, synthetic status and scientific verification. Source-linked
library restrictions and tombstones remain effective and intake receipts stay unverified.

## Independent publication refusal

This package offers no operation to enable publication. A fixed default-held publication
contract is independent of capture/member/gate changes. Service-only
`collection_publication_capabilities()` returns exactly
`{"version":"gsip-collection-publication-v1","publication_allowed":false}`.
Missing/unknown capabilities refuse export as well. Supported export checks this before any
candidate/photo read, cached artifact reuse or Hub call, and again at publication boundaries.
The real source adapter requires an explicit known scope per row; pure export/aggregation
rejects pilot or unknown scope before constructing public artifacts.

Database guards refuse the public-cell refresh RPC and positive writes to public cells and
release records, including service-role writes. Deletion that only removes public exposure may
remain possible. Existing public rows/releases are not modified by installing the migration.
An aggregate-only refresh request cannot prove which source rows it includes. Reopening
publication therefore needs another reviewed source-bound aggregation contract and migration;
a configuration flip in this package cannot reopen it or clear immutable pilot classification.
Existing individual-spectrum, photo-calibration and field-training holds remain unchanged.
Unrestricted administrators/credentials are not claimed protected from deliberate exfiltration.

## Browser account, queue and rights flow

Existing-account email OTP sets `shouldCreateUser: false` and uses an allowlisted same-origin
return URL. It never upgrades or creates an anonymous account in pilot/rights mode. Authentication
alone is insufficient: membership and current server gates are rechecked before every write and
retry. Auth changes invalidate admission and stop further writes. Missing/expired/revoked,
wrong-owner, unowned or incompatible legacy queue rows hold without rebinding or spending retry
budgets. A rights refusal remains terminal where existing withdrawal rules require it.

A dedicated explicit browser rights view restores an existing account and exposes `YourData`
while capture/library intake are closed or invitation membership is revoked. It cannot drain,
queue or upload. The default closed landing and native builds do not initialize auth/network
merely by loading. The same rights view is the rollback destination; operational cleanup and
rights processing must continue under a separately approved deployment plan.

A pilot observation still requires A+B, location/protocol and contributor grant; linked sample
context and optional bounded instrument-declaration JSON use existing LIB-4. No original
instrument files, lab reports, physical-pair verification, optical extraction, field training
or real peer federation is added. Existing disclosed coarse-cell enrichment remains applicable.

## Artifact contract

A separate explicit `invited-pilot` browser build uses a dedicated output, never Capacitor's
`dist`. Its strict activation receipt binds a mode, exact project/API origin and web origin,
both collection flags and publication-held status. Unknown, missing, contradictory or mismatched
inputs refuse building/packaging. Only the reviewed target may pass deployment packaging. A
closed/rights-only rollback remains closed for new writes and preserves rights access.

Ordinary `build:pages` and native builds retain their exact two-key false/false receipt and
existing validators. Pilot receipts cannot be copied into either path. A separate manually
invoked review-artifact build is not a deployment or environment approval. No production pilot
artifact is generated in this source authorization. Synthetic tests use reserved `.test`/
loopback targets, isolated temporary output, no real keys and no publication. Every deploy
packager refuses those synthetic artifacts. No secret is embedded in any receipt or report.

## Proof and later operator handoff

Tests first fail on current behavior: exact capability/target/receipt refusal; no anonymous
fallback/account creation; current membership and queue ownership; default/native isolation;
private classification immutability; every authenticated/privileged write bypass; manual export,
map/release writes and pilot aggregation refusal; lost responses; revocation/withdrawal races;
rights after closure; sanitization/cleanup and held publication. Existing SQL positive fixtures
must explicitly establish invited accounts and gates; do not add a production legacy bypass to
make earlier tests pass. Explain changed publication-positive assertions as a stronger held
contract, preserving their original privacy/ownership protections and independent coverage.

Independent review and green CI precede the implementation merge decision. Local Docker daemon,
PostgreSQL/PostGIS/pgTAP, GDAL and Android tooling are unavailable in the current shell; report
what ran locally and rely on actual CI results for those checks. No local pass proves a physical
phone, native storage, delivered email, operating worker or production deployment.

The operator handoff lists all pending migrations, row counts, advisors and effective RLS/
Storage/auth/worker checks; matching adopted notice URLs/terms version; invited-account steps;
cleanup/sanitization/withdrawal proof; exact artifact digest, activation/rollback commands and
target. Each production operation waits for Justin's separate exact-command go and stops on
mismatch. A real consenting-participant phone rehearsal is separately authorized and reported
with counts/status only. Code/CI does not open capture, library intake, publication or native
field collection.
