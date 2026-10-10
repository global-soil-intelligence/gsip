# Contributing to GSIP

GSIP accepts one work package per pull request. Read `docs/SPEC.md` and
`docs/BUILD_ORDER.md` before changing code.

## Workflow

1. Open or select a work-package issue.
2. Branch as `wp-<id>-<slug>`.
3. Add tests for every behavior change.
4. Run `pnpm lint && pnpm typecheck && pnpm test && pnpm build`,
   `uv run ruff check . && uv run mypy && uv run pytest`, and, when you change
   the database, `pnpm db:start && pnpm db:reset && pnpm db:test`.
5. Use Conventional Commits and sign off every commit with `git commit -s`.
6. Complete the pull-request checklist: acceptance criteria, invariants I1–I15
   and business guardrails B1–B8.

Never commit credentials, precise contributor locations, raw public image
metadata, or fixtures containing real contributor information. Report security
issues privately as described in `SECURITY.md` rather than opening a public
issue.

## Contributions written with AI agents

Agents are welcome contributors, under the same rules as people plus one more:
every agent-authored change has a **human of record** who reads it, runs the
checks and answers for it (SPEC I9).

- Add a `Co-Authored-By:` trailer naming the agent or model to each commit it
  wrote.
- The human of record signs off (`Signed-off-by:`). An agent never certifies
  the DCO and never approves a pull request.
- Say in the pull request which parts an agent wrote and how you verified them.
- Agents follow the same privacy rules: no real contributor data in prompts,
  fixtures or logs, and no service-role credentials in agent tooling.

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

Credentials, API keys, private keys, `.env` files, contributor or partner data, or real photos of
people or property. The secret scan blocks known key formats. If you find a leaked secret, report it
privately as described in `SECURITY.md`.

## Names and marks

The license does not cover GSIP or Viridis names, logos or certification marks. See `TRADEMARKS.md`.
