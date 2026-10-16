# Invited browser pilot: held operator handoff

**WP-COLLECT-2 #82. Source/testing only; no production command in this work was executed.**

Approved source scope: invited adult phone-browser contributors using existing owner-provisioned
accounts. Capture/library intake, signup, anonymous sign-in, workers, publication and deployments
remain unchanged. This document is a preparation checklist, not a production go or permission to
create an account. Real-phone/delivered-email proof and native device/backup proof remain separate.

## What the source changes

- Private owner-admin invitation membership; a revoked/anonymous/nonmember user cannot collect.
- Every new submission is immutably private_pilot, regardless of optional library context or QA.
- Both existing capture and library gates must admit writes. Missing/old capabilities refuse.
- Fixed publication refusal covers the real exporter, manual public-cell refresh and positive
  cell/release writes. No release-enable operation exists. Pilot rows cannot later be promoted.
- Existing-account email recovery never creates an account. Browser `#your-data` (and its exact
  `?view=your-data` email return) remains a rights-only destination when intake is closed.
- Default Pages/native outputs retain exact false/false receipts. A separate reviewed browser
  candidate path binds the source and target; it has no deployment command or permission.

## Known production baseline, not fresh activation evidence

The 2026-10-16 read-only baseline was 28 migrations, capture closed, no library tables, 5 contributors,
25 submissions, 25 photos, 0 auth users and 0 public cells. Signup/anonymous signin were off, five scheduled
worker jobs held, and a separate security-advisor read returned zero findings. No operator may
reuse that dated evidence as activation approval. Refresh it and stop on any unexplained change.

The source now includes three pending migrations relative to that baseline:

1. `20261013030000_wp_lib4_private_intake.sql`
2. `20261014010000_wp6fa_private_photo_privacy.sql`
3. `20261016225028_wp_collect2_invited_private_pilot.sql`

A fresh dry-run must establish the actual pending list. Never apply it implicitly. Before a
migration on this row-bearing project, run `scripts/db-migration-test.sh`; present the exact
commands and target `toxldjgwkxtneoqsazym` for Justin's separate go. An approved application of
exactly these three would result in 31 migrations, with counts/gates unchanged and zero security
findings; a mismatch stops the operation. Never reset production or weaken RLS.

## Decisions and gates before any real records

1. Resolve/adopt/publish complete notices and matching immutable terms version; contributors
   accept personally. Confirm working privacy/support contact, adult pilot bounds and retention.
   Verify the inviting organizer can process deletion of an unused provisioned Auth account:
   before its first observation it has no contributor row, so the app must truthfully refer
   that account-only request to the organizer rather than claim an in-app deletion was filed.
2. Record cohort capacity/duration and any explicit narrow exceptions to remaining public-launch
   calibration/tile/paid-tier gates. The invited choice does not waive those prerequisites.
3. Verify target schema, effective RLS/Storage and advisor findings after a separately approved
   migration. No invitation is automatically backfilled; existing seed rows are not pilot proof.
4. Present exact owner-provisioned-account and private membership enrollment commands privately,
   with target and expected counts, for a separate go. Keep signup/anonymous signin off. Verify
   a delivered email, the exact canonical Auth redirect allowlist and same-origin callback without reporting emails, tokens or sessions.
5. Prove bounded sanitization, raw cleanup, rights/deletion and the private publication hold
   under separately approved operations. A secret name or green source test is insufficient.
   Keep cleanup/rights operating after rollback; closing intake does not withdraw a grant.
6. Only after these gates, propose the exact reviewed source and artifact preparation command
   for a separate go. The manually dispatched `collection-build.yml` requires main and the
   owner-protected github-pages environment. It only uploads a review artifact; it never deploys.

## Candidate review and later activation

The candidate builder requires an exact clean checkout matching the reviewed 40-character SHA,
canonical project/origin, browser-safe public key and a new isolated output. It builds the
ordinary site closed first, then a separate invited browser output. Strict receipts and a
SHA256 file inventory bind the candidate to the source and reviewed target. Synthetic fixture
receipts, stale/symlinked outputs, unknown fields/targets or modified bytes refuse packaging.
No canonical open artifact was generated in this source authorization.

Future command shape (placeholders are intentionally not executable approval):

```text
uv run python scripts/build_collection.py --reviewed-sha <EXACT_REVIEWED_MAIN_SHA>
  --project-ref toxldjgwkxtneoqsazym --site-origin https://globalsoilintelligence.com
  --prepare-review-artifact
```

Do not run it until its exact invocation receives Justin's go. Review the resulting Actions
artifact digest, source, inventory and activation receipt. Then present a separate exact
Pages-deployment/database-gate plan and a tested rollback plan for another go. Ordinary Pages
must not be used to sneak in a pilot receipt; its independent closed validator is unchanged.
Opening capture or library intake remains an owner operation, not an effect of code merge.

A confirmed server rights request remains confirmed if local device cleanup fails. Rehearse
that failure separately: report pending local cleanup without claiming the server request failed,
and never clear a replacement account. The support route must handle that recovery.

Rollback stops new collection and drains while retaining the explicit rights view and supported
recovery, cleanup/deletion and effective withdrawal. Recheck expiry, wrong-owner queues and
retries. Neither rollback nor reopening permits publication or erases immutable release copies.

A separately authorized consenting-participant phone rehearsal must verify private receipt,
exact retry, retained sanitized photos, raw cleanup, withdrawal/account deletion and no public
output. Reports contain only counts/status/digests. Browser engine tests are not a physical
phone, actual email delivery, hosted advisor run or evidence of independently verified spectra.

## Limits retained

The intake accepts finalized A+B photographs, context and optional bounded instrument-declaration
JSON. It does not ingest original instrument files/lab reports, verify physical pairing, extract
field optical features, train field models or synchronize real peers. Coarse-cell enrichment
still uses the disclosed processors. Photo publication/calibration, individual spectral release,
native storage/device, signing/store and wider public-service gates remain separate.
