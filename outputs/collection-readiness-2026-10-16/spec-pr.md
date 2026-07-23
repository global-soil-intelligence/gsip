## Problem and result

The closed capture page attributes collection delay to legal review. Justin directed on 2026-10-16 that outside counsel must not be a prerequisite for starting soil collection. This v14 proposal records that decision and replaces counsel approval with Justin's adoption of complete contributor notices. Consent, privacy, withdrawal and the existing licences remain required.

WP-COLLECT-1 documents a concrete first-collection path and the missing technical work. It proposes a bounded private browser pilot, held pending the owner's audience/account choice, reviewed WP-COLLECT-2 implementation and separate production approvals. It does not implement or activate that mode. Closes #78.

## Invariants and scope

- Preserve I1–I15 and B1–B8: exact locations/raw uploads stay private, contributors accept immutable grants themselves, withdrawals remain effective and licences are unchanged.
- Keep capture, hosted library uploads, public signup, anonymous sign-in, workers, publication and native/device gates unchanged.
- Preserve the ordinary Pages/native closed-artifact checks. A future collection path needs its own reviewed strict mode/manifest validation and enforceable publication hold, including manual export/public-cell paths.
- Documentation only: no runtime code, schema, dependency, workflow, configuration, credential, production or licence changes.

## Evidence and validation

- Fresh read-only production metadata/counts: 28 migrations, capture false, no library tables; 5 contributors, 25 submissions, 25 photos, 0 auth users, 0 public cells. The two later source migrations are not deployed.
- Independently verified public Auth settings: signup disabled, anonymous sign-in false, email the only enabled provider. All five scheduled worker jobs held. These reads do not establish a fresh advisor or effective RLS/storage audit.
- `pnpm lint`: passed (ESLint, language guard and all Markdown formatting).
- `uv run pytest tests/test_processors.py`: 6 passed. A sandbox prevented writing pytest's optional cache; test execution passed.
- Independent read-only review: all findings resolved; `git diff --check` passed.
- No behavioral test is added to this documentation-only policy proposal. The separate WP-SITE-1H UI repair and held WP-COLLECT-2 have explicit negative behavioral regressions.

## Assumptions and unresolved decisions

- Justin's instruction removes the outside-counsel project gate; it does not adopt placeholders, waive consent, determine legal compliance or authorize production changes.
- Invited adults using a browser is a recommendation, not a selected audience. Capacity, duration and account method remain owner decisions.
- Public-launch calibration, tiles and paid-tier gates are not silently waived. Any narrower pilot exception needs a bounded owner decision and recorded impact.
- Private intake currently accepts finalized A+B photographs, context and optional bounded instrument-declaration JSON. It does not upload original instrument files/lab reports, verify physical pairing, train field models or enroll real federated peers.
- Current production evidence is dated 2026-10-16 and must be refreshed before any operation. Existing seed rows are described only by counts.
- Contributor notices remain drafts until Justin resolves factual inputs, adopts a complete version and publishes matching URLs/terms version.

## Changes after review

- Removed two overlooked legacy counsel gates in SPEC's contribution terms and BUILD_ORDER's PR review checklist, aligning them with the owner decision.
- Added independently verified Auth and worker holds to the readiness matrix, and explicitly bounded the read-only evidence so it cannot be mistaken for security-advisor/RLS proof.

Codex authored the amendment; Justin Hart remains human of record and final reviewer. No DCO certification, approval, merge, deployment or collection opening is performed.

## CI evidence

At exact head `57c5a1033a807855da19507588c259012fcdbd9c`, [validate run 38975170779](https://github.com/global-soil-intelligence/gsip/actions/runs/38975170779) completed successfully on 2026-10-16 at 22:30:30 UTC. This includes the browser, GDAL/Python, Deno, populated-migration and disposable database/pgTAP checks. Both secret scans passed; the internal-branch DCO job was skipped rather than certified by an agent. No merge or production operation followed.

## Additional read-only production evidence

After the metadata/Auth audit, a separate targeted security-advisor read of `toxldjgwkxtneoqsazym` returned `results: []` and the explicit status "No issues found" at all security levels (info and above). This is advisor evidence, not an assertion that the missing intake schema is deployed or that post-migration RLS/storage/collection operations have passed. No production mutation occurred.

## Next source package

[WP-COLLECT-2 #82](https://github.com/global-soil-intelligence/gsip/issues/82) tracks the held implementation, including an explicit tested withdrawal route/channel after rollback closes intake. Current closed builds hide YourData, so rights continuity must be proven rather than inferred. The tracking issue selects no audience and grants no production authority.
