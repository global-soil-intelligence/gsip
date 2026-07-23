## Problem and proposed behavior

WP-COLLECT-4 / SPEC v17, following owner-approved source merges #86 and #87. An optional live framing guide can make the invited phone-browser flow easier without requiring a printed reference card. This PR specifies the interaction, lifecycle, image limits, private queue boundary, exact future source scope and acceptance evidence. It implements no camera feature.

The proposed first version uses one explicitly started video-only preview, a plain SVG outside the saved full-frame JPEG, and review before use. It starts a separate empty-observation guide session with photos in RAM until an owner-bound queue commit. Switching to the existing picker confirms loss of those unqueued guide selections. A guide or RGB photo supplies no calibration, instrument spectrum or biological result.

Closes #88 as a design deliverable only; COLLECT-4A/4B remain held for Justin's design review and separate implementation go.

## Invariants and acceptance

- [x] Restated I1–I15, L1–L7 and B1–B8. I5 language, I7 privacy, I9 personal acceptance and I12 public-agent boundaries remain binding; no licence change or dependency.
- [x] Preserve required A+B/optional C, real depth and strict declarations only on explicit library opt-in, private invited admission, owner/rights/withdrawal and all publication holds.
- [x] Specify one pending media request/encoder, bounded resources, stale callback disposal, background holds/revalidation, accessible fallback and actual decoded-pixel exclusion tests.
- [x] Specify atomic queue identity reconciliation, exact context consume, new-commit revision fence, observable stale-writer refusal and no blanket draft cleanup. Declare the narrow existing App/LibrarySection/queue changes explicitly before implementation.
- [x] Freeze prospective scope/resource/privacy choices with mutation guards; demonstrate failure before the manifest and before the review-added completion guards, then success.
- [x] Independent design reviews completed; findings and corrections recorded below.
- [ ] Justin's design choices and implementation approval. No runtime capability or physical-phone qualification is claimed by these prospective tests.

## Assumptions and decisions for owner review

1. Version one serves the invited, existing-account browser pilot only; default/native/rights/ordinary browser paths retain the picker. This does not open or deploy that pilot.
2. Accept RAM-only guide photos and no mixed picker/guide observation initially. Reload can lose selections; no OS backup or RAM-erasure guarantee is made. Durable/mixed drafts need a later ownership contract.
3. Accept full-frame video JPEG with provisional 1280/720 minimum edges, 2048 maximum edge, quality 0.92 and explicit fallback. These are engineering bounds, not scientific thresholds. Browser colour conversion/lossy encoding remain possible.
4. On background, pending work is discarded and the camera stops; already accepted RAM photos may remain held until fresh same-context validation. Dropping all photos is an alternative owner choice.
5. No new native code/permission, service, dependency, store/version, backend/grant format or activation flag. Source/CI review grants no actual-camera, field/device, migration, deployment or collection authority.

## Verification

- Local: `pnpm lint`, `pnpm typecheck`, `uv run ruff check --no-cache .`, `uv run mypy` passed. Temporary writable cache paths used for local Python tools.
- Local: 129 focused Python tests passed, including 36 prospective design/mutation guards and existing specification/iOS design/scope/backup regressions. No camera or contributor data used.
- Red evidence: missing prospective manifest failed; missing completion/reconciliation/writer guards failed before they were added. These are scope guards, not camera implementation tests.
- Main after merges: CI [38988142286](https://github.com/global-soil-intelligence/gsip/actions/runs/38988142286), Android/iOS [38988142311](https://github.com/global-soil-intelligence/gsip/actions/runs/38988142311), and secret scan [38988142210](https://github.com/global-soil-intelligence/gsip/actions/runs/38988142210) succeeded at a2529906. Both Android debug APK and iOS simulator artifacts exist.
- This PR's required CI will be recorded after it runs. No local full database, GDAL, Android or Xcode execution is claimed for this docs-only package.

## Changes after review

- Independent media review: narrowed colour-preservation wording to no application-added correction; browser conversion and lossy JPEG are explicitly acknowledged.
- Independent state/queue review: added atomic revision advance for each new guide commit, original-revision library/picker writers, observable refusal, and both transaction-order tests. This prevents a late library write from resurrecting consumed IDs or showing refused persistence as ready.
- Clarified existing-identity outcome reconciliation before consumed-draft/original-revision checks, preserving stored sync progress and the frozen pending identity after its own completion revision.
- Coordinated existing focus/auth refresh paths with the proposed single outstanding access refresh; no overlapping replacement after a soft timeout.

Agent-authored design and tests: Codex. Justin Hart is the human of record. No human DCO certification or PR approval is supplied by the agent. No production changes; protected Pages runs caused by #86/#87 were cancelled and both live activation flags remain false.
