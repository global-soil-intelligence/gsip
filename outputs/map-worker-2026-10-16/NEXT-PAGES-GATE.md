# WP-SITE-1G — next Pages gate

Status: prepared; no merge, new Pages run or deployment executed. The live website still serves approved run 38821460183/source 73088050d6fc68baedf893990ab3fbe76d5e749c. Its old GitHub redirects now pass all eight trusted HTTPS route checks; both upload gates are closed.

## Reviewable repair

PR: https://github.com/global-soil-intelligence/gsip/pull/77

Exact repair head: `d53eda2e835e57b4ee01dc922fb63d5ebdeceae0`.

The worker and its dependencies are explicitly bundled and configured before map construction. Full existing dependency notices accompany the build; project licences and dependencies are unchanged. Both root and repository-subpath browser regressions fail on the old artifact and pass on the repair. Independent review's notice finding is resolved. Exact-head CI run 38894216993 is successful, including GDAL, migration-over-existing-data, Deno and pgTAP. Both gitleaks jobs pass; DCO skips under the unchanged in-repository policy. Effective main rules currently omit a required-status-check rule: validate passed but is not server-required. Making it required remains Justin's originally reserved action; no rule was changed.

Local closed artifact: `gsip-site-1g-closed-pages.tar.gz`, SHA256 `d748a201546fff7b8e71a555ee5abb492cdcb2bffb62d8265dd42c9a160e3d01`, 40 files / 6,623,128 unpacked bytes. It uses existing public repository configuration and forces both flags false. The map is 2,422,310 / 5,242,880 bytes. The receipt is `closed-pages-artifact-receipt.json`; this is a local preparation artifact, not a pending GitHub deployment or an approval-bound production artifact.

## Why a valid run waits for merge go

The existing `github-pages` environment permits only branches `main` and `gh-pages`. Justin is its sole required reviewer, with administrator bypass disabled. A repair-branch dispatch would not satisfy the branch restriction, so no such dispatch or policy change is proposed. Root AGENTS.md/BUILD_ORDER reserve the merge go for Justin; this implementation request is not that go.

After exact-head green CI and Justin's explicit approval to merge #77, the proposed bounded command from the repository root is:

```sh
gh pr merge 77 --repo global-soil-intelligence/gsip --merge \
  --match-head-commit d53eda2e835e57b4ee01dc922fb63d5ebdeceae0 \
  --subject 'fix(site-1g): land verified map worker packaging (#77)' \
  --body-file outputs/map-worker-2026-10-16/merge-body.PROPOSED.md
```

This proposal is not executed. Do not approve the PR, certify Justin's DCO, bypass protections or merge the unrelated draft #73.

The authorized merge would trigger the existing `pages.yml` push-to-main workflow. No manual workflow dispatch is necessary. Read back the merge commit, find that exact source's Pages run, wait for its build only, and verify the environment still requires Justin. Inspect and hash its actual uploaded artifact, both strict false flags, worker/notice files and budgets. The merged-source build may have different fingerprints from this local repair-branch artifact; never substitute its local hash for the actual run's hash.

Present that new run URL, source commit and artifact digest for a separate Pages deployment go. Until that explicit go, never submit the pending-deployment approval endpoint or bypass an environment protection. Capture and library intake remain closed after every step.

## Deployment verification after a later go

Once the actual run is explicitly approved, verify its successful deployment; trusted HTTPS apex/www and original GitHub redirects; exact artifact file hashes; worker JavaScript/notice delivery; real browser console and map processing; prerendered navigation/llms.txt; and closed capture with no upload form. This plan authorizes none of those production changes in advance.
