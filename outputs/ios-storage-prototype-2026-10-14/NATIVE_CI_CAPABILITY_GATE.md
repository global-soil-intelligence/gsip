# APP-2C2A: hardware CI decision, not installation authority

Status: PROPOSED; no runner, account, service, workflow or production change has been made.

## Verified blocker

Candidate `ac70c8d17d0568e555c9422635ff1791f1c70ded`; PR #73 remains draft.
Hosted run: https://github.com/global-soil-intelligence/gsip/actions/runs/38669675164
Toolchain: Xcode 27.0 / 27A266a; simulator 27.0 / 24A434.

The owned synthetic base reports all existence/type/owner/private-mode/link/size/identity predicates true and backup exclusion true. Protection query and property availability are true, but exact complete-protection readback is false. Volume-support query and property availability are true, but `volumeSupportsFileProtection` is false. Source ordering proves this fixture stopped before attempting nonce-root creation or SQLite open/create. Database metadata was uninspected because its ancestor was not admitted; its false diagnostic fields are unavailable observations, not direct absence proof. The 15 actual SQLite fixture cases fail at the preserved boundary; 27 other core cases pass. The command later times out; its teardown cause is not established. The owned simulator was shut down and deleted.

This establishes a capability failure on this hosted filesystem. It does not establish that every hosted image or provider lacks it. No other runner has been proven suitable. Raising a timeout does not repair the failed protection readback.

The same exact commit passed the complete pipeline on Justin's current Apple-silicon Mac: 42 core + 33 host native cases, zero failures/skips; both ordinary Debug/Release compile/link/bundle/ZIP isolation audits. Its fixed negative-control metadata reports complete protection and volume support true. The intentionally false root exclusion is distinctly labelled CONTROL and never treated as fixture-failure evidence. This is simulator metadata proof only; physical encryption, passcode and backup/restore acceptance remain held.

## Recommended path

Prepare a separately reviewed, protected hardware CI lane that executes the unchanged full native suite on an explicitly selected Apple-silicon Mac with the required capability. Keep #73 draft and the strict failing check until that lane actually passes. Preserve exact complete protection, exclusion, all assertions, zero-skip acceptance, the complete structured test tree and artifact-isolation audits.

Prefer a dedicated machine. If Justin offers the current Mac, use a separately approved isolated OS account and setup design first; do not attach a general runner to his everyday account. A runner executes repository code, so account/runner registration and execution authority must be explicit and bounded. No account or runner setup is authorized by this proposal.

## Concrete proposed work-package scope

1. Specification/BUILD_ORDER amendment first, in a separate docs PR. Bind the hardware target, trusted workflow/revision policy, permission boundary, lifetime and removal protocol. Do not add files or expand native APIs in #73.
2. Preserve existing Linux validation, Android, ordinary iOS and full-history secret scans. Native runtime policy and tests remain unchanged.
3. Propose a dedicated `native-storage-ci` protected environment with Justin as required reviewer, no production/service-role/signing secrets, and a trusted reviewed candidate revision. Do not allow unattended fork code onto the hardware. Exact environment/runner settings require their own approval.
4. Use an ephemeral runner registration for one approved job, read-only repository permissions and an isolated disposable checkout/work directory. No persistent service, login item or shared working copy by default. Registration material stays in GitHub's secret mechanism; do not send it in chat, commit it or log it.
5. Pin and verify the same Xcode 27.0/27A266a and simulator 27.0/24A434. Frozen dependency installation, both activation flags false and unsigned simulator builds remain mandatory.
6. Execute the existing helper and all 75 native cases on a newly created run-owned simulator. No existing device/app/user data, macOS host Keychain item operation, signing, passcode change or production connection. Require actual protection/exclusion readbacks, zero failures/skips, complete authored case identities and actual Debug/Release artifact isolation.
7. Upload only the validated sanitized receipt. Retain raw logs/xcresults privately; publish no path, nonce, payload, private metadata or contributor data. Ordinary APK/simulator artifacts stay separate.
8. Verify the exact-head PR context green, receipt and artifact inventory; then remove the ephemeral runner registration and disposable simulator/work directory. Stop on any failed cleanup or identity mismatch. Do not merge #73 without a separate owner go.

## Approval sequence and missing input

First, Justin identifies an available dedicated Apple-silicon Mac, chooses a separately isolated account on this Mac for design review, or keeps the PR held. This is a hardware availability/design choice, not installation permission.

After the host is identified and the design is reviewed, prepare the exact setup/registration/workflow commands and target before asking for a separate setup go. No generic token-pasting commands or account actions are supplied here. No paid service, new machine purchase, security exception, relaxed check or production action is approved.

If no suitable hardware is available, keep the native check and PR held. Any alternative acceptance contract would require an explicit, separately documented owner exception; it is not the recommended path and will not be implemented under the current scope.

## Existing governing boundary

`docs/IOS_NATIVE_SCOPE.md` reserves exact native files/effects and states: "Every assumption is a stop gate." The user's current go requires keeping the approved safeguards and authorizes no production or capture opening. The implementation scope is still exactly 21 native + 3 support files; all 377 existing files and nine frozen bindings remain unchanged.

Assumptions: a selected hardware/account can provide the same capability as the verified local run; ephemeral protected execution can be configured without exposing unrelated data; the owner has available suitable hardware. None is treated as proven or as setup authority.
