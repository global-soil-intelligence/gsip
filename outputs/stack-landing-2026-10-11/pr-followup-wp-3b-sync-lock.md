## Problem and behavior

Two website tabs can concurrently send the same IndexedDB queue record. WP-3b wraps the complete queue drain in `navigator.locks.request('gsip-sync', { ifAvailable: true }, …)`. A busy context returns without reading or mutating the queue; browsers without Web Locks keep existing idempotent behavior.

## Invariants and acceptance

- [x] One same-origin drain owns the lock until its promise settles; no waiting when busy.
- [x] Account, withdrawal, generation/cancellation, retry/backoff and dead-letter semantics stay unchanged. Private queue data remains private.
- [x] Unsupported Web Locks retain the previous drain.
- [x] Regression tests cover concurrent contexts, busy/no queue access, unsupported contexts and exception release. Three failed without the implementation; all five pass.

## Verification

Local: 307 Vitest; 220 pytest with four GDAL skips; lint, typecheck, Python Ruff/mypy, closed-capture web/app builds, map/site budgets and pinned Gitleaks 8.21.2 staged scan passed. Current PR CI is pending. GDAL and Deno were unavailable locally; a real two-tab browser smoke was not run.

Assumptions: the browser supplies standards-compliant origin-scoped Web Locks; the tests simulate two contexts with a shared manager. Existing online/30-second triggers retry a skipped drain. The existing per-screen generation counter and separate queue mutations are outside this lock's scope.

## Authority and assumptions

- Justin Hart is product owner and human of record; Codex wrote this follow-up. Justin reviews and merges. No merge, approval, deployment or capture opening occurred.
- This PR starts from green WP-APP-1 head `f9e1ac2` and stays stacked there until the reviewed stack merges. Existing reviewed commits are preserved.
- Capture and production anonymous sign-in stay closed. I5, I7, I12 and B1–B8 remain binding. MIT code, ODbL 1.0 data and CC BY-SA 4.0 photos are unchanged. No dependency added.
