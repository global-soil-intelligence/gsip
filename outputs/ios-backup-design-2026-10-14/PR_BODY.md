The approved iOS no-cloud policy is still unverified: source inspection of the current filesystem bridge found best-effort exclusion without readback/error propagation, non-atomic writes and destination deletion before rename. Moving the private queue with that API would not prove the required protection.

This specification-only proposal adds SPEC §15.10 and a complete storage inventory/evidence contract. BUILD_ORDER separates APP-2C1 feasibility, held APP-2C2 migration and APP-2C3 owner-authorized physical-device backup/restore evidence. No backend is selected, no runtime/dependency changes are made and no native-language exception is inferred.

Refs #67.

### Explicit invariants

- Preserve I1–I15, B1–B8, existing §11 launch gates, §15.1–15.9, all §16 library gates and all 122 existing acceptance-checkbox lines/states.
- Preserve offline durability, original-account ownership, revision/generation fences and combined six-store queue/reminder rights clearing.
- Require excluded containment before private writes, propagated errors/readback, actual transaction guarantees and classified WebKit/native/camera residual coverage before selecting any backend.
- Keep production, capture/sign-in, workers, photo calibration/publication, signing/accounts and device readiness separately held. No precise points, raw uploads, session values or real contributor data enter evidence.

### Changes

- Document exact source limitations, native-resolution caveats and full persistence inventory in `docs/IOS_PRIVATE_STORAGE.md`.
- Define migration/crash/restore/downgrade and synthetic physical-device acceptance without claiming implementation or device proof.
- Add 15 policy cases that fail without this specification. No existing runtime, dependency, scanner rule or workflow changes.

### Verification actually run

- Local full repository lint (ESLint, language, Prettier), Ruff and diff whitespace checks passed.
- Local focused policy suite: 39 passed, zero failures/errors/skips. New tests on the unmodified baseline: 15 expected failures, zero errors/skips.
- Independent adversarial review: 30 focused tests passed; removing exclusion, migration and device-proof sections produced 2, 2 and 1 expected failures. Verified all 367 source-manifest files, 363 unchanged files and byte-identical existing normative sections/checkboxes. Separate primary-source review found no blocking factual findings.
- Gitleaks 8.21.2, non-shallow full history/all local refs, redaction on: 157 commits scanned, no leaks. Exactly the existing four approved historical fixture suppressions; ignore/config hashes unchanged.
- Hosted CI pending at PR creation. No local database/GDAL/native/device/backup experiment is claimed; corresponding required source checks run in CI. Docs-only changes do not trigger native app artifacts.

### Assumptions and reserved decisions

- Justin's approved no-cloud policy remains binding; approval of this proposal does not select a backend or permit custom native code. TypeScript/Python-only remains in force.
- Exact source inspection describes capability limits, not observed device leakage or a universal backup guarantee. ION native versions are an observed generated resolution, not a repository-native lock.
- No suitable backend has yet satisfied this complete contract. Recommended next work is source-only feasibility/audit while iOS release readiness remains held; a concrete mechanism needs its own review, and custom native implementation needs Justin's explicit language exception.
- No new dependency or licence/service change is proposed. No signing/account/device inputs are assumed available. Existing cloud backups cannot be retroactively retracted by the app.
- Codex authored this proposal/tests; independent agents reviewed source accuracy and policy risks. Justin Hart is human of record. No agent approval or DCO certification is asserted.

### Acceptance

- [x] Exact-source feasibility proposal with complete persistence/residual inventory.
- [x] Existing invariants, launch/library gates and checkbox states preserved.
- [x] Failing-before/passing-after policy tests and independent review.
- [x] Required hosted checks green.
- [ ] Justin reviews the proposed specification; backend selection and any native-language exception remain separate decisions.

### Changes after review

- The draft incorporates initial independent-review requirements for exclusion before any private byte, actual atomic transaction/single-writer proof, logical-versus-physical erasure, camera/cookie residuals, restore/rights fences and exact native-resolution limits. Final frozen-source and factual reviews found no blocking findings. No post-commit code change was needed.

### Final exact-head CI evidence (2026-10-14)

Head `476bbdab190c99a3bb6d5d8143f21bebde6baf9f`: [validate passed](https://github.com/global-soil-intelligence/gsip/actions/runs/38557797439), [PR secret scan passed](https://github.com/global-soil-intelligence/gsip/actions/runs/38557797394) and [branch secret scan passed](https://github.com/global-soil-intelligence/gsip/actions/runs/38557758174). DCO was skipped by the existing workflow, not agent-certified. CI verified 1,968 Python tests passed / 31 real-tool skips, 12 browser tests, mypy over 76 source files, Deno checks, data-preserving migration suites (13/13, 19/19 and the additional 13/13 scope), and 593 pgTAP assertions in 11 files. Lint/typecheck/JavaScript tests/build/map budget and disposable database lifecycle steps all succeeded. No new native artifacts are expected for these docs/policy-only paths; no device/backup proof is inferred.

Final independent commit/scope closure verified parent/main, only four changed paths and all 367 committed blobs against the reviewed manifest; Conventional Commit and Codex co-author trailer are present, with no Signed-off-by. The PR remains a draft proposal for Justin's specification review, with backend/native implementation decisions separately held. No production operations or merges ran.
