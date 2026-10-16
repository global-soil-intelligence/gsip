# First soil collection: readiness and owner decisions

**WP-COLLECT-1 / SPEC v14 proposal — 2026-10-16. No production authority.**

Justin directed that outside counsel must not delay starting soil collection. This records
that project-policy decision and prepares the technical path. It does not adopt incomplete
terms or claim legal compliance. Public capture and hosted library uploads remain closed.

## What can collect now

The [local library tools](SOIL_LIBRARY.md) can store private sample/measurement JSON under
the operator's control, offline. They do not register a hosted node or synchronize real peers.
For the website/phone path, LIB-4 source is merged but requires deployed schema, its separate
server gate, both app activation gates and a valid contributor account. It collects a finalized
A+B photo set, sample context and optionally a bounded instrument-declaration JSON file. It
does not accept an arbitrary node archive, original instrument file or lab report. A successful
receipt means `stored_private_unverified` or `already_stored`, not verified paired evidence.

## Proposed first hosted collection

Recommend an invited, adult, browser-only pilot, with bounded duration/capacity chosen by Justin.
Use owner-provisioned accounts and keep public signup and anonymous sign-in disabled. The app
must require a valid invited login and never auto-create an anonymous account. Existing code's
email login is not proof of that complete first-use flow; WP-COLLECT-2 must implement and test it.
Public self-service collection is an alternative requiring an explicit account/abuse-control
plan and the owner's CAPTCHA/provider/hosting decisions. The audience is not selected by this
proposal; the request for the owner's preference remains open.

Keep pilot submissions and linked records private, with ownership/RLS, quotas, provenance,
immutable grants, holdout and withdrawal controls. Photographs must have working sanitization
and raw-upload cleanup. Retain the disclosed coarse-cell ISRIC/USDA/Open-Meteo enrichment unless
a reviewed source change disables it; holding a scheduled prior worker does not stop the app's
immediate prior request. Do not promise that no external processor is called.

No pilot record is exported, published as a photo/spectrum, added to public map coverage or used
for field training. A disabled schedule does not prevent a manual export or refresh. WP-COLLECT-2
must specify and test an enforceable collection-only publication boundary covering those paths.
The existing photo-screening/calibration and individual-spectrum/fingerprinting gates remain.

## Factual contributor notice before activation

Justin must adopt the actual notice/terms/sampling text and an immutable matching terms version.
Complete the controller/contact, audience/age, retention and processor inputs; describe the
private/unverified collection scope, deletion/withdrawal path and later publication separately.
No agent accepts for a contributor, publishes placeholders as effective terms, changes a
licence or retroactively rewrites an existing grant. Counsel may be consulted, but outside
counsel sign-off is not this project's collection prerequisite.

## Readiness matrix

| Item                          | Current evidence / remaining work                                                                                                                                                                                                                                                                                                                                                                                       |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Public website/map            | Pages run 38895620835 deployed from 27c3d914; both activation flags false; map worker and redirects verified on 2026-10-16.                                                                                                                                                                                                                                                                                             |
| Hosted schema                 | Fresh read-only production query on 2026-10-16: ledger 28, capture false, no library tables. LIB-4 `20261013030000_wp_lib4_private_intake.sql` and WP-6fA `20261014010000_wp6fa_private_photo_privacy.sql` are source, not deployed evidence.                                                                                                                                                                           |
| Counts only                   | Fresh readback: 5 contributors, 25 submissions, 25 photos, 0 auth users, 0 public cells. No contributor contents were read.                                                                                                                                                                                                                                                                                             |
| Collection build              | Ordinary Pages workflow hardcodes false/false; packaging independently refuses an open manifest. WP-COLLECT-2 needs a separately reviewed mode/manifest/artifact path; keep default/native paths closed and protected approval effective.                                                                                                                                                                               |
| Contributor accounts          | Fresh public Auth-settings readback: new signup disabled, anonymous sign-in false, email the only enabled provider; 0 auth users. Select the audience/account flow; do not create accounts or enable signup during preparation.                                                                                                                                                                                         |
| Notices and grants            | Drafts remain unadopted; owner must resolve inputs, adopt complete text, publish its URLs/version and verify grant acceptance/rejection behavior.                                                                                                                                                                                                                                                                       |
| Cleanup, rights, QA           | Fresh repository readback: all five scheduled worker jobs held; prior/QA/export workflows disabled, cleanup/rights workflows active but their schedule variables absent. Source alone is insufficient. Verify deployment compatibility, credentials, sanitization and processing/withdrawal/deletion using approved bounded rehearsals before real data. A stored photo is not evidence it survived quarantine cleanup. |
| Publication hold              | Default-closed schedules alone are insufficient. Specify/test collection-only export/public-cell/photo/spectral holds, including manual paths. No export or release is authorized.                                                                                                                                                                                                                                      |
| Existing launch prerequisites | 50-photo QA calibration, prior tiles, paid hosting and other §11 gates remain required for public launch. Any limited pilot exception needs its own bounded owner decision and impact record.                                                                                                                                                                                                                           |
| Native app                    | Device, backup, notification and signing/store gates remain separate. This proposal does not approve iOS/native field collection.                                                                                                                                                                                                                                                                                       |
| Required CI protection        | `validate` passed at the deployed source but is not server-required; owner action remains outstanding.                                                                                                                                                                                                                                                                                                                  |

These production and Auth reads were verified independently on 2026-10-16 at 22:16 UTC. They establish metadata/counts and public Auth settings, not a fresh security-advisor result or effective RLS/storage audit. No production mutations were performed.

## Sequence and acceptance evidence

1. Review/merge the specification; Justin chooses the audience and any bounded pilot exceptions.
2. Build/review WP-COLLECT-2. Negative tests prove closed defaults, strict collection-mode
   packaging, sign-in refusal/no anonymous fallback, missing-capability refusal before writes,
   wrong-owner/race/retry/withdrawal behavior and enforceable publication holds. Rehearse only
   synthetic records in disposable/local targets; never publish those fixtures.
3. Refresh production counts, schema, auth, storage/RLS, worker holds and security findings.
   Run `scripts/db-migration-test.sh` before proposing migration on this row-bearing project.
   Show the exact pending list and exact commands for `toxldjgwkxtneoqsazym`; wait for a separate
   migration go. After migration, verify ledger, unchanged counts/security and closed gates.
4. Adopt/publish the complete notices/version, configure only the approved account/provider/tier
   choices, and prove the cleanup/rights/sanitization path and publication hold under separately
   authorized bounded operations. Report failures; do not infer readiness from a secret's name.
5. Build the exact approved collection artifact and rehearse rollback. Present its digest,
   mode, audience, database gates, deployment target and exact activation/rollback commands.
   Wait for Justin's separate go before any deployment, auth change or gate opening.
6. Verify a consenting participant's phone journey privately. Put only counts/status receipts
   in reports; no coordinates, photographs, e-mails, tokens or sample payloads in public output.
   Verify the private receipt, exact retry, sanitization, withdrawal/deletion and held publication.

No exact activation commands are executable yet: WP-COLLECT-2 and the owner's unresolved choices
determine them. This plan authorizes preparation only. Keep the established production-change
gate and stop on any preflight/readback mismatch.
