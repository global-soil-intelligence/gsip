# Contributing to GSIP

GSIP accepts one work package per pull request. Read `docs/SPEC.md` and
`docs/BUILD_ORDER.md` before changing code.

## Workflow

1. Open or select a work-package issue.
2. Branch as `wp-<number>-<slug>`.
3. Add tests for every behavior change.
4. Run `pnpm lint && pnpm typecheck && pnpm test && pnpm build` and
   `uv run ruff check . && uv run mypy && uv run pytest`.
5. Use Conventional Commits and sign off every commit with `git commit -s`.
6. Complete the pull-request acceptance checklist and declare affected
   invariants I1-I8.

Never commit credentials, precise contributor locations, raw public image
metadata, or fixtures containing real contributor information. Report security
issues privately to the project owner rather than opening a public issue.
