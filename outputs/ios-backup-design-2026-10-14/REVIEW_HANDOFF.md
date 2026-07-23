# iOS backup feasibility proposal — 2026-10-14

PR: https://github.com/global-soil-intelligence/gsip/pull/68 (draft, unmerged). Issue: https://github.com/global-soil-intelligence/gsip/issues/67.

Source head: `476bbdab190c99a3bb6d5d8143f21bebde6baf9f`; parent/main: `2c6caa15cbc381eb1c0e3a0b47f40847ef2210c1`.

The four changed files are SPEC, BUILD_ORDER, the new iOS private-storage evidence/design document and 15 policy tests. No runtime, dependency, workflow or licence change. All 367 committed source files match the independently reviewed frozen manifest. Existing I1–I15, launch/library sections and 122 old acceptance-checkbox lines/states remain identical.

Local checks: full lint, Ruff, diff check, focused 39 tests passed with zero skips. The 15 new tests fail on the unchanged baseline. An independent 30-case review passed; removal of exclusion, migration and device-proof sections caused expected failures. Two independent reviewers closed design/source accuracy without blocking findings. Gitleaks8.21.2 reported157 commits scanned and zero leaks with redaction, non-shallow/all-ref history, the same four approved historical suppressions and unchanged scanner configuration.

Hosted validation passed at the exact head: https://github.com/global-soil-intelligence/gsip/actions/runs/38557797439. Both branch and PR secret scans passed. DCO was skipped by the existing workflow, not certified. CI: 1,968 Python pass/31 skips, 12 browser pass, mypy76 source files, 593 pgTAP assertions/11files, Deno and data-preserving migration checks, lint/typecheck/JavaScript/build/map budget all passed. Source/CI metadata and only extracted summary counts are preserved; full CI log was not persisted.

## Next step and limits

The existing filesystem bridge does not prove backup exclusion/error readback or crash-safe replacement. The proposal therefore selects no backend. Recommended: keep iOS release readiness held and complete source-only feasibility for a suitable upstream open mechanism. APP-2C2 migration waits for an exact reviewed supported mechanism; custom native code would additionally require Justin's explicit exception to the current TypeScript/Python-only rule. APP-2C3 physical backup/restore proof needs separately authorized synthetic device/account/signing inputs.

No production queries/changes, deployment, merge, worker dispatch, Pages approval, capture/sign-in opening, account/signing changes or real contributor data access occurred. No native/device build or cloud backup experiment is claimed. CI supplies GDAL, Edge Function and disposable database verification; no hosted site-budget or new native artifact pass is inferred.

Assumptions: existing no-cloud policy and language guard remain binding; exact source findings describe capability limits rather than observed leakage/device proof; generated ION resolution is not a universal repository lock; old provider backups cannot be retroactively retracted. Approval of this specification does not grant a native-language exception or production authority.

The prior library/source landing report remains immutable in outputs/stack-landing-2026-10-11/library-landing-v9-2026-10-13/. It is a historical source receipt, not a current production-health claim.
