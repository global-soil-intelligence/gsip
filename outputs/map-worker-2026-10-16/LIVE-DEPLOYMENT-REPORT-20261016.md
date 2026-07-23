# Approved Pages release: live verification complete

Status: **DEPLOYED AND VERIFIED — CAPTURE AND LIBRARY UPLOADS CLOSED.**

Justin explicitly approved Pages run `38895620835` in this turn. This report supersedes the earlier prepared/held release status; all earlier evidence remains unchanged.

## Release identity and authorized action

- Site: https://globalsoilintelligence.com/ ; map: https://globalsoilintelligence.com/map/ .
- Repository: `global-soil-intelligence/gsip`; protected environment: `github-pages`, ID `18657050755`.
- Successful run: https://github.com/global-soil-intelligence/gsip/actions/runs/38895620835 , attempt 1.
- Deployment: `7118088317`, success at **2026-10-16 14:45:45 EDT** (18:45:45 UTC).
- Source: `27c3d9143ff78dce65fa4d2e88e1660c79574232`; tree `d49fa2ef6b31a0042db64d74e78b8a12df5b758b`, equal to reviewed PR #77.
- Artifact: `12043617713`, ZIP SHA256 `d818ff8663588d7eb12bdf691b92127ee6ca61495c4e6ab9c08eae1c596fbc0b`.
- [PR #77](https://github.com/global-soil-intelligence/gsip/pull/77) was merged under the previous explicit go; its reviewed-head CI and [merged-main CI](https://github.com/global-soil-intelligence/gsip/actions/runs/38895620789) passed. No PR was merged or approved in this deployment turn.

Root's strict preflight at 18:45:23 UTC matched the waiting run/attempt/source, unchanged main, successful main CI, actual local artifact digest and all 40 files, both false activation flags, pending environment/reviewer and administrator-bypass hold. Only then was the previously presented command submitted once:

```sh
gh api --method POST \
  repos/global-soil-intelligence/gsip/actions/runs/38895620835/pending_deployments \
  --input "/Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/map-worker-2026-10-16/pages-approval-request.PROPOSED.json"
```

GitHub readback confirms build and deploy succeeded for the exact source; pending approvals are now empty. A parallel independent preflight read landed after the approved transition and correctly recorded that the run was already in progress. That receipt is preserved; it was not used to bypass the root's prior matching preflight.

## Live verification

- **40/40 live files** match the actual approved artifact by exact byte count and SHA256, including prerendered pages, `llms.txt`, capture assets and the map. Strict trusted TLS and bounded same-origin destination checks were used.
- Worker: HTTP 200, `application/javascript`, 509,702 bytes; SHA256 `096f3b4deeeaa7ed1372a96978bea3495b78250041df835fada34f12320e11d2`.
- Full dependency notice: HTTP 200, 32,566 bytes; SHA256 `9aa4807394e33c6a38be8c590001a791203e703d9afefa0e7c2f47b1655a1dce`.
- Real Chrome rendered the live SoilGrids map. Switching organic carbon to pH changed the selected control, legend and rendered layer; zoom interaction worked. No first-party warning or error was captured. Six unrelated browser-extension warnings were excluded explicitly in the browser receipt.
- The live public-contribution state is **“No QA-passed public contributions yet.”** This is expected with capture closed; no claim of live contributor-cell processing or new observations is made. Actual worker processing with synthetic public-shaped H3 features was proven by the reviewed build's regression tests.
- Apex and www trusted HTTPS pass. All **8/8** canonical/legacy routes pass, preserving intended paths and actual artifact bytes. Old `global-soil-intelligence.github.io/gsip/` URLs redirect directly to HTTPS on the canonical domain, including `/data/` and `og-library.png`; there is no HTTP downgrade.
- Live `capture/gsip-activation.json` is exactly `{"capture_live":false,"library_intake_live":false}`.
- The live capture page displays **“Contributions open after our launch review.”** It has zero forms, zero file inputs and zero buttons. No upload or sign-in was attempted.

## Scope, assumptions and remaining gates

Only this approved Pages deployment was released. No DNS, environment protection, repository variable, Supabase database/auth/function, worker schedule, photo publication, export or capture setting changed. Existing public configuration and upstream ISRIC WMS remain in use. No new dependency or licence change was introduced.

The website packaging/redirect acceptance holds are resolved by current live evidence. This does not open public collection or certify calibration, legal approval, mobile storage/device checks, store signing or full product launch. `validate` remains a successful check that is not server-required; Justin's separate required-check action remains outstanding.

## Evidence

- `pages-go-preflight-20261016.json`
- `pages-approved-readback-20261016.json`
- `live-final-independent-20261016T184639Z.json`
- `pages-run-38895620835-artifact-verification.json`
- `live-map-browser-readback-20261016.json`
- `live-map-38895620835.jpg`
- `live-capture-closed-20261016.json`
- `live-capture-closed-20261016.jpg`

The final receipt binds these files by size and SHA256. No secrets or contributor data were printed or added to the report.
