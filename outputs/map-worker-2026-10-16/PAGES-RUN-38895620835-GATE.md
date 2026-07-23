# WP-SITE-1G: actual Pages release awaiting approval

Status: **BUILT, ARTIFACT VERIFIED, DEPLOYMENT NOT AUTHORIZED.**

This supersedes the pre-merge proposal in `NEXT-PAGES-GATE.md`; the earlier file and local preview archive remain historical preparation evidence. Justin explicitly authorized merging #77 while holding Pages for separate approval. The authorized merge is complete. No pending-deployment approval has been submitted.

## Exact release target

- Repository: `global-soil-intelligence/gsip`.
- Website: `https://globalsoilintelligence.com/` and its existing approved aliases.
- Environment: `github-pages`, ID `18657050755`.
- Run: https://github.com/global-soil-intelligence/gsip/actions/runs/38895620835 (attempt 1).
- Merge/source commit: `27c3d9143ff78dce65fa4d2e88e1660c79574232`.
- Source tree: `d49fa2ef6b31a0042db64d74e78b8a12df5b758b`, exactly equal to reviewed head `d53eda2e835e57b4ee01dc922fb63d5ebdeceae0`.
- Artifact: `github-pages`, ID `12043617713`, 40 files / 6,623,136 content bytes.
- Official and independently computed ZIP SHA256: `d818ff8663588d7eb12bdf691b92127ee6ca61495c4e6ab9c08eae1c596fbc0b`.
- Embedded TAR SHA256: `bc5ab24a2ff6ca54c92cf09db589ac98a5233c7c101013fc1886c09e1605d769`.
- Build succeeded; deploy waits for Justin. Required reviewer remains `jdhart81`, administrator bypass is disabled, and only `main`/`gh-pages` may deploy. No protection changed.
- Merged-source CI run `38895620789` succeeded at 2026-10-16 11:52:32 UTC; its secret scan `38895620824` succeeded. Independent final readback at 11:53:22 UTC confirms this Pages run still waits for approval.
- Capture and library intake flags are both `false` in the actual artifact. Existing live activation flags were independently read back as both `false`.

The actual map contains its worker (509,702 bytes), all existing upstream licence notices, and stays at 2,422,310 / 5,242,880 budget bytes. The actual run's capture files differ from the local pre-merge preview only through the existing CI commit-version suffix (`+27c3d91`) and its generated filenames/precache references. Use this actual-run digest, never the local preview archive digest, for release approval.

## Exact proposed command — do not execute before a separate go

The following approves **only this pending Pages deployment**. It does not dispatch workers, deploy Edge Functions, migrate Supabase, change repository variables/DNS, approve or merge another PR, open capture, or enable library uploads.

```sh
gh api --method POST \
  repos/global-soil-intelligence/gsip/actions/runs/38895620835/pending_deployments \
  --input "/Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/map-worker-2026-10-16/pages-approval-request.PROPOSED.json"
```

Immediately before executing after a go, read back the exact run/source, artifact digest and pending protected environment. Stop on mismatch or if it has already deployed, expired, been cancelled, or been superseded. The local proposed payload is preparation only; its existence is not permission.

## Verification after a later go

1. Confirm this run's deploy job succeeds for the same source and artifact.
2. Fetch the actual 40 live files and compare their hashes to `pages-run-38895620835-artifact-verification.json`.
3. Check the worker responds 200 with JavaScript MIME, full notices respond 200, and a real browser can render/process the map without worker/resource/console failures.
4. Verify trusted apex/www HTTPS and the old GitHub URLs preserve their direct HTTPS redirects, including a nested page and image.
5. Check prerendered pages, `llms.txt`, and capture remains closed with no upload form; read back both activation flags as `false`.
6. Record outcomes honestly. No future deployment/activation is authorized by this document.

## Remaining owner action

The effective main ruleset lacks a required-status-check rule. `validate` passed on the reviewed head, but is not currently required by GitHub. Justin reserved making it required; no rule was modified. This remains a separate launch/protection action.

## Assumptions

- Reuse the existing Pages custom domain, public repository variables and protected environment without changing them.
- The pinned MapLibre worker and native index shape used by the regression remain as reviewed; a future dependency upgrade may need an intentional test update.
- Local browser evidence uses synthetic public-shaped cells only. No contributor data, raw uploads or private locations were used.
- This is a website packaging repair, not proof of scientific calibration or full product launch readiness.

Evidence: `merge-readback.json`, `pages-run-artifacts.json`, `pages-run-38895620835-artifact-verification.json`, the independent actual-artifact review, exact-head/main CI receipts, and `redirect-recheck-independent.json`. The screenshot `pages-run-38895620835-waiting.jpg` shows the actual pending approval.
