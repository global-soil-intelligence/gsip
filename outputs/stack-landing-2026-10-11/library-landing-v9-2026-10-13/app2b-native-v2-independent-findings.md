# Independent APP-2B native evidence review

Status: changes requested. Four P2 findings remain on the frozen candidate. No GitHub review or approval was submitted.

Freeze:
- Patch SHA-256: 10c45f8a6425119865d9d0c0fc3ec0951f4352b42b19e611e4d84a80b4e6c9bb
- Author receipt SHA-256: 1907c5ae2065402d773e3778a5a524d90a8ef6c14491fcd03a1c94035775cef4
- Script SHA-256: c05c7074035f8695d6f0df37e65449808e63396c7639ac79cd9f7f415ec75c65
- Exact baseline: d7ed716ed0921381da04f542e90902ede36cb462. Twelve mandatory governing/build/workflow files independently matched that Git object; full mandatory instructions were read.

Only the baseline and four frozen files were copied. The isolated integration additionally copies the owner-designated immutable privacy disclosure at SHA b5458b944ef3b1b9895ef9ac1870ecfbd94c8345aabd1644e54eae1e9654bf2d. No other mutable APP core file was read. Review-only adversarial tests were added only in the isolated copy.

## Findings

1. [P2] Reject traversal before root or coordinate binding (scripts/app_notification_audit.py:82-94, 474-487). `Path.absolute()` preserves `..`, and `is_relative_to` is lexical. `allowed/../outside` reads bytes outside its sole permitted root. A synthetic runtime artifact path starts beneath the declared module/version cache path then climbs six parents to an unrelated external JAR; the audit accepts that JAR under the original coordinate. Reject traversal components and validate normalized containment while preserving no-follow/symlink checks. Both independent refusal probes currently fail because no exception is raised.

2. [P2] Reject duplicate POM identity and license fields (scripts/app_notification_audit.py:220-241). `find` and `findtext` select the first match. A coordinate-matched POM with two versions (1.2.3 then 9.9.9), or two license names (Apache-2.0 then Proprietary commercial runtime), is accepted. This contradicts the documented ambiguity and unknown-license refusal. Validate singleton parent/coordinate fields and required singleton license-name/URL fields before interpreting inheritance/licensing. Both independent refusal probes currently fail because no exception is raised.

3. [P2] Validate required native audit evidence before comparison (scripts/app_notification_audit.py:850-861). The comparison accepts sidecars containing only schema/platform/commit/lock/key headers, with no runtime graph, npm sources, POM licenses, binary hashes, SPM selection or tree evidence. It emits an overall feature result and hashes those incomplete sidecars. Validate exact required platform-specific audit shape, nonempty complete graph/native inputs and source input binding; missing evidence must refuse. The independent missing-native-graph refusal probe currently fails because no exception is raised.

4. [P2] Bind SPM revision to the selected checkout (scripts/app_notification_audit.py:631-639). Any 40 lowercase hex characters are accepted as the 8.5.2 revision, without reading back the checked-out package revision or a reviewed exact revision/manifest. The unchanged valid synthetic manifest/archive/tree passes after only Package.resolved revision changes to ffffffffffffffffffffffffffffffffffffffff. Verify the actual checkout matches the resolved revision and the approved release selection; unknown or mismatched revisions must refuse. The independent refusal probe currently fails because no exception is raised.

## Actual checks

See independent-checks.json for exact argument vectors, statuses and log SHA-256 values.
- Frozen native focused suite: 53 passed.
- Four-file baseline plus frozen privacy dependency: 130 passed across native audit/build/permissions/processors. Before that explicitly supplied integration disclosure, 129 passed and one preserved processors host-disclosure guard failed; tests/test_processors.py was never changed.
- Independent seven synthetic probes: six expected-refusal failures, one passing wrong-coordinate refusal. The six failures substantiate the four findings above. No network request was made.
- Independent closed-SDK guard mutation: removing the selected-module closed-SDK check makes its authored refusal test fail (exit 1). Exact script bytes were restored and their hash rechecked.
- Ruff: passed for both frozen Python files.
- mypy: passed for both frozen Python files.
- Prettier: passed for workflow and documentation using the supplied Node 24 runtime/dependency.
- Eleven multiline Bash workflow bodies pass syntax checks; a first-command failure in the dependency pipe exits 1 under Bash -e -o pipefail.

Source review confirms all prior candidate Android/iOS permission, compiled backup/closed activation/version, actual repeat-build and closed-SDK gates remain. Parent uses the fixed d7 commit in its isolated runner-temp clone, frozen copied installs, same job/config/toolchain/run number/shared disposable debug key, with both actual repeats. New audit files are workflow triggers. No Pages, production worker/environment, signing-account, secret-scanning/rules/ignore-file change is in this four-file patch. The honest overall-feature-delta and ZIP-entry versus full-byte labels are retained.

Limits: no native SDK/Xcode/device/store/production execution, native transitive license result or measured native-size outcome was attempted or claimed. Header-only comparison and unknown-revision permissiveness need fixes before review closure. Root owns the combined 23-file integration/full CI, branch/PR/merge and owner gate decisions.
