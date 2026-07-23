# WP-SITE-1F independent review

Date: 2026-10-15. Reviewer: Codex independent review agent (`site_library_review`).
Reviewed the uncommitted `wp-site-1f-spectral-library` diff in `/Users/justinhart/.codex/worktrees/gsip-spec-followups/GSIP 2.0`.

**Final status: no open findings in the reviewed source diff.** This is an independent source review, not a GitHub approval, merge authorization, production verification or Pages deployment approval.

## Scope

- `apps/site-web/src/App.tsx`: five public pages, builder/demo links, navigation, JSON-LD, scientific and maturity claims, privacy and release boundaries.
- `apps/site-web/src/styles.css`: the new development-status styling.
- `apps/site-web/index.html`, `apps/site-web/about/index.html`, `apps/site-web/card/index.html`, `apps/site-web/data/index.html`, `apps/site-web/methods/index.html`: descriptions, social metadata and preview references.
- `apps/site-web/scripts/prerender.mjs`: non-JavaScript/agent content and configured destination wording.
- `apps/site-web/public/og-library.png`: visually inspected the social preview; its mission and development-stage text read correctly.
- `apps/site-web/tests/app.test.tsx`, `apps/site-web/tests/prerender.test.tsx`, `tests/e2e/agent-readable.spec.ts`, `tests/e2e/shells.spec.ts`: regression intent, preserved closed capture journey, scientific boundaries, hydration and crawler coverage.
- `docs/BUILD_ORDER.md` and `package.json`: work-package registration, constraints and mission description.

Compared against SPEC §11 and the relevant §16 library contracts, I5/I7/I11/I12, governance and repository contribution rules. Applied the React best-practices source-review checklist. No new hooks, data fetching, dependencies, publication path or activation setting was introduced by this diff.

## Resolved finding

The initial review found that a configured Hugging Face URL still became “the latest release” in generated `llms.txt`, contradicting the updated website's more careful destination wording. Re-read the fix: it now says **“configured destination; check published status and contents.”** The claim no longer infers a release from configuration alone.

## Preserved boundaries

- Public capture and hosted library uploads remain visibly closed; no gate, production workflow or service setting is changed.
- Phone RGB stays uncalibrated and distinct from measured spectra. Same-physical-sample measurements, independent evaluation and actual biological assays remain prerequisites for scientific claims.
- Public releases stay structured-only pending deployed and approved photo screening. Individual spectra stay private pending fingerprinting/privacy review.
- The demo is explicitly synthetic; local nodes do not imply canonical acceptance, public enrollment or real sharing.
- MIT, ODbL 1.0 and CC BY-SA 4.0 remain explicit. Precise locations, private records and holdout labels are not newly exposed. Agents retain public-only read access.

`git diff --check` passed during the initial review and after the wording fix. Test suites, responsive browser checks, CI, GitHub-description readback and Pages artifact/deployment approval are verified separately by the root agent; this review does not claim those executions. The existing canonical-domain cutover remains separately gated.
