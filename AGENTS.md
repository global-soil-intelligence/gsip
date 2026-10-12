# Coding agents working on GSIP

Help Justin Hart build, manage and deploy GSIP as a technical collaborator. Justin is the
product owner and human of record; Viridis LLC stewards the project. Carry authorized work
through verification and a reviewable pull request, and report evidence and blockers honestly.
This file guides repository contributors. [The API-consumer guide](docs/AGENTS.md) explains
public REST and MCP access for agents using GSIP data.

## Read first

Read the [SPEC](docs/SPEC.md), including invariants I1–I15 and section 11 launch gates, and the
[BUILD_ORDER](docs/BUILD_ORDER.md) in full before a work package. Also read
[CONTRIBUTING](CONTRIBUTING.md), [GOVERNANCE](GOVERNANCE.md), the
[deployment runbook](docs/PHASE1_DEPLOYMENT.md), [app-store plan](docs/APP_STORE.md),
[legal-pack status](docs/legal/README.md) and [configuration example](.env.example).

The v3.0 documents originated on `docs/spec-v3`; use that reviewed specification until it
lands on `main`. Do not silently replace it with older documents on `main`. If governing
instructions conflict, flag the conflict. Justin's explicit instructions take precedence.

## Before each change

- Restate explicit invariants: what must stay true and what the change adds. Implement to
  them, then add tests that fail without the change and prove the behavior.
- Choose one work package per PR and a `wp-<id>-<slug>` branch. Architecture changes need a
  specification update first on `docs/spec-v<n>`, with approval before implementation where
  Justin has reserved the decision. Register new work packages in BUILD_ORDER.
- Flag every assumption in the PR description. Include acceptance criteria, touched I1–I15
  and B1–B8, actual verification results and unresolved review findings.
- Use Conventional Commits. Add `Co-Authored-By: Codex <codex@openai.com>` to each commit
  written by Codex; another agent names itself. An agent never adds Justin's `Signed-off-by`,
  certifies the DCO, approves a PR or merges. Justin reviews and merges.

## Preserve the reviewed stack

The ordered reviewed branches are `docs/spec-v3`, `wp-6b-launch-hardening`,
`wp-6c-priors-and-tiles`, `wp-6d-contributor-rights`, `wp-6e-provenance`,
`wp-agent-1-read-api` and `wp-app-1-phone-app`.

Never rewrite these commits, rebase these branches or force-push. Fix forward: commit on the
branch owning the defect, then merge that branch into every later branch in order. Keep
existing PR descriptions and append each fix and reason under **Changes after review**.
When Justin merges a predecessor, retarget the next PR to `main` and resolve conflicts by
merging `main` into it. Follow-ups stack on `wp-app-1-phone-app` until the reviewed stack merges.

The only approved secret-scan exception is the three immutable synthetic WP-AGENT-1 fixture
fingerprints in `.gitleaksignore`, audited on 2026-10-11. Do not broaden them or change the
scanner's rules, full-history coverage, redaction or workflow to make a check pass. Any
additional suppression requires Justin's explicit approval.

## Privacy, security, language and dependencies

- I7: precise contributor coordinates, raw uploads and private metadata never enter public
  output, logs, fixtures, issues or PR text. Use no real contributor data in development,
  tests or prompts. Public observation locations remain k-anonymous cells.
- I12: agent-facing code never uses the service-role key or a user session. Public readers
  use the publishable key and anonymous database role. Never weaken RLS.
- Secrets live only in GitHub or Supabase secret stores. Never commit, print or paste them;
  Justin supplies credentials through `supabase login` and the secret stores.
- I5: UI and API copy describes estimates with uncertainty; follow the terminology enforced
  by `scripts/check-language.mjs`.
- TypeScript and Python only. No paid or closed service or proprietary SDK in the default
  deployment path without Justin's sign-off (BUILD_ORDER guardrail 6). Android's permission
  and closed-SDK checks must stay effective. For every new dependency, document its licence,
  maintenance signal and size.
- Licences stay MIT for code, ODbL 1.0 for data and CC BY-SA 4.0 for photos. Any licence
  change is Justin's decision. Business guardrails B1–B8 remain binding.

## Verify from the repository root

Use Node 24 or newer and the pinned pnpm/uv configuration. Install without changing lockfiles:

```sh
pnpm install --frozen-lockfile && uv sync --frozen --all-groups
```

Run the checks appropriate to the change, and all required CI checks before reporting ready:

```sh
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm check:map-budget
pnpm check:site-budget
pnpm --filter @gsip/capture-pwa build:app
pnpm exec playwright test --project=desktop-chrome
uv run ruff check .
uv run mypy
GSIP_REQUIRE_GDAL=1 uv run pytest
deno check --config supabase/functions/deno.json supabase/functions/*/index.ts
scripts/db-migration-test.sh
```

The following database commands are **local only**, for the disposable Supabase development
stack. Confirm the target before resetting it:

```sh
pnpm db:start && pnpm db:reset && pnpm db:test
```

Docker, GDAL (`gdal-bin`), PostgreSQL with PostGIS and pgTAP, the Android SDK and Xcode are
needed for the corresponding checks. State missing tools and rely on CI for those results.
Never report a check as passing unless it ran. Preserve command outcomes, run links and
artifact evidence; a local pass does not prove a deployment or production health.

Before browser verification, inspect the Playwright setup. If it builds Pages with
`VITE_CAPTURE_LIVE=true`, flag that conflict with the closed-capture rule and leave that
setup unrun until Justin resolves it. Browser fixtures must use synthetic data and local
mock services.

## Production is gated, one step at a time

Never set `service_state.capture_open = true`, build Pages with `VITE_CAPTURE_LIVE=true` or
enable anonymous sign-in in production. Only Justin may open these gates after SPEC section
11 is satisfied. Owner-controlled Apple/Google accounts, signing, CAPTCHA, paid tiers and
new paid or closed services remain Justin's decisions.

The selected production project is `toxldjgwkxtneoqsazym` (`gsip`, `us-east-1`). Justin
reported it paused on 2026-10-11 and reserves restoring it to himself. Verify current state;
do not restore it. Destination approval does not authorize deployment.

Before **each** production migration or deployment, post the exact commands and target
project, then wait for Justin's explicit **go** for that step. Follow the deployment runbook
in order: database; Edge Functions; repository variables; workers; tiles; Pages. Record each
step as done with evidence, blocked with a reason, or Justin's action.

Before migration, report table row counts only, with no contents, and run
`scripts/db-migration-test.sh` before migrating a database holding rows. Never run `db reset`
against production. After migration, verify the security advisor reports zero findings and
`capture_open` remains `false`; never infer either from a successful command.

Deploy `prior-attach` with JWT verification on and `gsip-public` with it off only after the
respective go. Verify protocol 200, resolution-9 cell 400 and four MCP tools. Keep secrets in
their stores. Do not dispatch export until Justin has created the Hugging Face dataset and
set `HF_DATASET_REPO` and `HF_TOKEN`. Tile-host approval remains conditional on the owner
policy and deployment go. Deploy Pages with capture closed, then check prerendered pages and
`llms.txt`. DNS, required `validate` status, counsel's legal approval and legal URLs, CAPTCHA,
Supabase paid tier and opening capture are Justin's actions.
