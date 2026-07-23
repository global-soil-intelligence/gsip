## Problem and result

Repository coding agents had no root guide collecting the governing documents, verification commands and owner authority. WP-AGENT-0 adds `AGENTS.md`, links the separate API-consumer `docs/AGENTS.md`, and registers the package in BUILD_ORDER.

## Invariants and acceptance

- [x] Reviewed stack immutability, owner-only approvals/merges and per-step production go remain explicit.
- [x] Privacy, public-only agent access, fixed licences, secret stores and closed-capture rules remain explicit.
- [x] Read-first links, root/workspace check commands, browser project and database/Deno targets resolve in usability tests. Both tests failed before the guide and pass afterward.

## Verification

Two guide usability tests, targeted Ruff/mypy, terminology check, changed-document Prettier and diff checks passed. PR CI is pending.

Assumptions: this consolidates existing authority without granting new permission. The prescribed browser harness produces synthetic local mock output, which is never published; deployable Pages must be rebuilt with capture closed.

## Authority and assumptions

- Justin Hart is product owner and human of record; Codex wrote this follow-up. Justin reviews and merges. No merge, approval, deployment or capture opening occurred.
- This PR starts from green WP-APP-1 head `f9e1ac2` and stays stacked there until the reviewed stack merges. Existing reviewed commits are preserved.
- Capture and production anonymous sign-in stay closed. I5, I7, I12 and B1–B8 remain binding. MIT code, ODbL 1.0 data and CC BY-SA 4.0 photos are unchanged. No dependency added.

## Changes after review

- `6d679f0` makes I5 explicit in the root coding guide: UI and API copy never says "soil test". The generic terminology reference alone did not state the owner's prohibition clearly enough.
- `ca275c4` adds a semantic regression assertion requiring the I5 prohibition to cover both UI and API copy. It fails against the pre-correction guide at `0a3fad1` and passes the corrected guide. All three guide tests, targeted Ruff/mypy, changed-document Prettier, the language guard and diff checks passed locally. No dependency, workflow or deployment authority changed.
- [CI validation](https://github.com/global-soil-intelligence/gsip/actions/runs/38192685396) passed at `ca275c4`; the secret scan also passed. This supersedes the earlier pending CI note while preserving the original verification record.
