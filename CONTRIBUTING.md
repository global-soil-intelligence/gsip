<<<<<<< HEAD
# Contributing to Global Soil Intelligence

## Sign your commits (DCO)

Pull requests from forks need a `Signed-off-by` line on every commit, matching the commit author's email:

    Signed-off-by: Your Name <you@example.com>

`git commit -s` adds it, and `git rebase --signoff origin/main` fixes an existing branch. Signing off
certifies the Developer Certificate of Origin 1.1 (https://developercertificate.org): you wrote the
change, or you have the right to submit it under this repository's license. The DCO check blocks
unsigned commits.

## License of contributions

Contributions are licensed under the same license as the files they change (see `LICENSE`), with no
additional terms. Don't submit work you can't license that way.

## Never commit

Credentials, API keys, private keys, `.env` files, customer or partner data, or wallet files. The secret
scan blocks known key formats. If you find a leaked secret, report it privately as described in
`SECURITY.md`.

## Names and marks

The license does not cover Viridis names, logos or certification marks. See `TRADEMARKS.md`.
=======
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
>>>>>>> origin/main
