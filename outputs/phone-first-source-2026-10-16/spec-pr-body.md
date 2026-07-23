The capture protocol already accepts photos without a printed card, while app/site instructions make printing sound mandatory. Clarify that existing policy before COLLECT-3 aligns the source copy and progressively reveals optional instrument details. A phone photograph remains uncalibrated camera evidence; measured spectra, physical samples and federation peers remain distinct.

Work package: specification prerequisite for WP-COLLECT-3, tracked in #85. Registers a separately held live-browser-guide design follow-up; no camera overlay is implemented here.

Invariants: preserve I1–I15, L1–L7 and B1–B8; required A+B/optional C; other quality/privacy/rights/admission gates; explicit sample registration and real declared depth; existing camera and permission policy; authenticated rights recovery; closed capture/library/default artifacts and production/photo/training holds. Adds explicit optional-card wording and a bounded source implementation/acceptance plan.

Validation: targeted Prettier checks and git diff --check passed. Required CI and independent adversarial review will be recorded below. This PR contains documentation only; no new dependency, licence, schema, runtime or production change.

Assumptions:
- Justin's “push these updates” authorizes preparing/pushing the bounded package A from the researched next-build brief. The live camera guide and unknown-depth/default sample registration remain separate follow-ups.
- No new capture protocol version or measurement tier is required because cardless acceptance already exists; the API shape remains unchanged.
- No field/device accuracy or universal-phone claim is made. Source/CI success does not prove deployment or collection readiness.
- Merge, Pages, migrations, account/invitation/worker actions and capture/library opening require their separate owner go.

Agent contribution: Codex authored this clarification for Justin Hart as human of record. No agent DCO sign-off or approving review.

## Changes after review

- Independent source review identified ambiguous wording that conflated photographs with extracted `camera_rgb` summary records. Commit 0b90464 distinguishes uncalibrated RGB source photos from the existing staged-only extraction contract; COLLECT-3 adds no extraction or automatic library records. All other reviewed card/depth/closed-rights boundaries were coherent.

## Verified CI and review

Exact head `0b90464b95266135ecd851e0bfb230a3e0f3bd11`: [validate](https://github.com/global-soil-intelligence/gsip/actions/runs/38985778729) passed, both secret scans passed, and DCO is skipped under the repository's agent policy. Fresh independent review confirmed no unresolved documentation issue, including the source-photo/extracted-record distinction. The separate implementation is #87. No merge, Pages or production action occurred; both activation flags remain false.
