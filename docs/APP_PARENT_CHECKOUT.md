# APP-2B isolated parent checkout

The Android and iOS feature comparisons build the exact baseline
`d7ed716ed0921381da04f542e90902ede36cb462` in a separate checkout. Both parent
steps clone the canonical public repository
`https://github.com/global-soil-intelligence/gsip.git`, then fetch that exact
commit into the new clone, check it out detached and verify `HEAD` before installing
or building. The candidate workspace is not the parent clone's object source.

The previous setup fetched the baseline into the candidate workspace before
cloning that workspace. Hosted iOS CI then failed to read the baseline tree. A
local synthetic partial-checkout fixture reproduces the same failure even though
the candidate fetch and local clone succeed. This fixture demonstrates the object
availability boundary; it does not establish the hosted runner's exact internal
object layout.

`tests/test_app_parent_checkout.py` executes the workflow's actual Git setup using
a local bare public fixture in place of the canonical remote. Its unadvertised
baseline is initially absent from the candidate clone. The tests verify baseline
contents, isolated objects, an unchanged candidate workspace, and refusal before
building when the baseline is missing or the checked-out commit is wrong. Removing
the explicit parent fetch also fails. No test accesses the network or real data.

The baseline hash, toolchain, frozen installs, build numbers, repeat builds,
source/license and permission audits, artifact comparisons and closed activation
flags retain their existing behavior. The public remote must remain available and
serve the exact baseline; failure stops the step. This source fix supplies no
hosted rerun, native-device behavior, iOS backup exclusion, signing, store-release
or production evidence.
