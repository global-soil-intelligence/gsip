## WP-COLLECT-2 — First hosted soil collection

**Held implementation proposal.** Depends on reviewed/merged #79 (SPEC §11.1) and Justin's audience/account choice. An invited adult browser pilot is recommended, not selected. No production, account, worker, merge, deployment or activation authority is granted here.

The merged code is not a working hosted intake deployment: production has ledger 28/no library tables, capture closed, signup/anonymous sign-in disabled and 0 auth users. All five scheduled jobs are held. The current Pages packager independently refuses open artifacts. Removing the outside-counsel prerequisite does not resolve these technical conditions.

## Invariants

- I1–I15 and B1–B8 remain binding, including contributor-controlled immutable grants, owner-bound private records, withdrawal, holdout, quota, no private details in output and no agent-facing service-role/user-session access.
- Keep ordinary Pages/native builds closed, strict manifest validation, protected Pages approval and all permission/dependency/security checks effective.
- Keep every real-data publication/model/federation gate held. Disabled workflow schedules alone are insufficient because manual export/public-cell paths exist.
- Keep MIT/ODbL 1.0/CC BY-SA 4.0, existing rights and disclosures. No new paid/closed service, dependency or operator credential without its existing audit/owner gate.

## Source work to specify and review

1. Implement an explicit, strictly validated browser collection mode/artifact path bound to the reviewed target. Unknown/missing/mismatched inputs refuse packaging; default/native paths still reject open artifacts. Define the additional schema/authority needed for collection-only publication exclusion before implementation; do not assume the two currently pending files are the whole future migration plan.
2. For invited mode, implement complete owner-provisioned email sign-in and recovery, refusing unexpected account creation and anonymous fallback. Existing `senderUid` automatically calls `signInAnonymously` for unowned records; the current email-linking flow is not a first-use invited login. Public self-service would need its own owner-approved abuse-control/CAPTCHA/provider plan.
3. Preserve library capability refusal before mutation, finalize A+B photographs, linked context and optional bounded instrument-declaration JSON, and return private/unverified receipts. Do not promise original instrument-file/lab-report ingestion, verified physical pairing, field optical extraction, training or real federation.
4. Enforce private-collection exclusion at all real export, public-cell refresh, photo, spectral and field-training paths, including manual paths and state/race/retry transitions. Define what happens to pilot records if a later public mode is enabled; no accidental promotion of unverified private records.
5. Prove sanitized private storage, raw-quarantine cleanup, quotas, owner/session binding, rights worker behavior and deletion/withdrawal under the reviewed target compatibility. Account and grant changes must not transfer queued records or restore withdrawn content.
6. Specify rollback without losing contributor rights. **Current App.tsx creates its client only when capture is live and renders YourData only under `live && client`; a closed web artifact hides in-app withdrawal.** Keep new writes closed after rollback while retaining a tested rights route or explicit effective supported withdrawal channel, with operational cleanup/deletion continuing. Do not present closed packaging alone as rollback proof.

## Acceptance evidence

- Negative behavioral tests fail on current behavior for strict mode packaging, invited login/no anonymous fallback, absent capability, invalid/expired/wrong-owner sessions and collection-only publication exclusion.
- Synthetic disposable/local end-to-end proof covers sign-in, accepted immutable terms, upload/context/declaration linkage, lost-response retries/idempotency, wrong-owner and withdrawal races, sanitization/cleanup, rollback and rights access after closing intake.
- Default Pages/native activation manifests remain false/false, while only the separately reviewed browser path admits its exact approved mode. No test fixture or synthetic payload is published.
- Independent adversarial review and green CI, including populated-migration/SQL-role tests for any new database contract. Audit each dependency's licence, maintenance and size; none is selected by this issue.
- Operator handoff lists every pending migration and exact command/target, fresh counts/advisors/RLS/storage/auth/worker evidence, actual owner-adopted notice URLs/version, account choices, artifact digest and activation/rollback plan. Wait for Justin's separate go before every production step.
- A separately authorized consenting participant phone rehearsal confirms private receipt, exact retry, withdrawal/deletion and no public output. Report counts/status only. Native device/backup/store gates remain independent.

## Assumptions and open choices

Outside counsel is not a collection prerequisite; basic contributor acceptance/privacy/licences remain. Audience, duration/capacity and any bounded exceptions to existing public-launch calibration/tile/paid-tier prerequisites remain Justin's decisions. Current production evidence is dated 2026-10-16 and must be refreshed before operations. This tracking issue schedules source preparation after its review prerequisites; it does not open collection.
