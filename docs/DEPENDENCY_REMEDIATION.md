# WP-SEC-1 dependency remediation

These are updates to four existing dependencies, not new capabilities or services.
Code/data/photo licenses, frozen installs, release-age policy, Android SDK checks
and full-history secret scanning are unchanged.

| Package                        | Locked version | License      | Maintenance signal                                                                   | Representative artifact size                                            |
| ------------------------------ | -------------- | ------------ | ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------- |
| source-map-js                  | 1.2.2          | BSD-3-Clause | Security release published 2026-09-30                                                | npm tarball 36,349 bytes; unpacked 142,723 bytes                        |
| uuid (only xcode's dependency) | 11.1.1         | MIT          | Patched CommonJS release published 2026-04-29; newer major releases remain available | npm tarball 19,965 bytes; unpacked 134,222 bytes                        |
| fsspec                         | 2026.6.0       | BSD-3-Clause | Maintained fsspec project; this compatible patched release published 2026-06-16      | Universal wheel 203,949 bytes                                           |
| multidict                      | 6.9.1          | Apache-2.0   | Maintained aio-libs project; patched release published 2026-09-21                    | Python 3.12 macOS ARM wheel 57,736 bytes; Linux x64 wheel 336,881 bytes |

Primary package registry metadata and artifacts were inspected on 2026-10-12.
These are package sizes, not measured APK or site growth.

The advisories are [source-map-js GHSA-68fv-2mgg-jv7q](https://github.com/advisories/GHSA-68fv-2mgg-jv7q),
[uuid GHSA-w5hq-g745-h8pq](https://github.com/advisories/GHSA-w5hq-g745-h8pq),
[fsspec GHSA-27vj-qcqg-25rc](https://github.com/advisories/GHSA-27vj-qcqg-25rc)
and [multidict GHSA-54p9-h82j-f925](https://github.com/advisories/GHSA-54p9-h82j-f925).

The source-map override covers both existing consumers. The UUID override is
scoped to `xcode`: its upstream manifest still asks for UUID 7 and its project ID
generator uses CommonJS `require`. UUID 11 retains that interface; versions 12+
are not substituted. Tests exercise the actual Xcode consumer and prove short
destination buffers are rejected by v3/v5; both bounds checks fail on UUID 7.0.3.
Native CI must still build both platforms and inspect their compiled artifacts.

`datasets` 5.0.1 requires fsspec at or below 2026.6.0, so a blanket latest-version
upgrade would break its declared constraint. Existing aiohttp permits multidict
6.9.1. Only these two Python package records were replaced with generated,
hash-bound resolutions; unrelated lock metadata is preserved. Frozen installation
and the existing dataset/export suites verify compatibility.

Dependabot #41 also refreshed unrelated PostCSS to a release less than one day
old, causing CI and both app builds to stop at the unchanged release-age check.
This package retains the age-eligible existing PostCSS resolution and replaces
#41's broader lock refresh. No age exemption is added.

No production deployment, dependency-alert dismissal or security check waiver
follows from this package. Read back alert state after merging rather than infer
zero findings from a successful install.
