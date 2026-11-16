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

# WP-SEC-2 dependency remediation

Three updates to existing dependencies. No new capability, service or package is added.

| Package              | Was    | Now    | License      | Why                                                                                                       | Released   | Unpacked size   |
| -------------------- | ------ | ------ | ------------ | --------------------------------------------------------------------------------------------------------- | ---------- | --------------- |
| zod                  | 4.6.5  | 4.6.6  | MIT          | [GHSA-mrhx-c7xc-m3w5](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5) (high)                           | 2026-10-11 | 6,148,944 bytes |
| serialize-javascript | 7.1.2  | 7.1.4  | BSD-3-Clause | [GHSA-m5mm-p8h7-m29v](https://github.com/advisories/GHSA-m5mm-p8h7-m29v) (low)                            | 2026-10-23 | 25,708 bytes    |
| vitest (and its set) | 4.1.11 | 4.1.12 | MIT          | [GHSA-qxg6-89mg-rqv8](https://github.com/advisories/GHSA-qxg6-89mg-rqv8) and GHSA-xp26-3454-mjgp (medium) | 2026-10-15 | 1,909,161 bytes |

Registry metadata was read on 2026-11-16. Sizes are package sizes, not measured site or app growth.

- **zod** validates input in two places that resolve it separately. The apps and `@gsip/schema`
  use the pnpm lockfile. The Edge Functions import the schema sources directly and resolve zod
  through `supabase/functions/deno.json` and `deno.lock`. Both now pin 4.6.6 with the same
  integrity hash, and a test keeps them equal. 4.6.6 is the smallest patched release; 4.6.7
  exists and was not taken. The advisory is memory exhaustion while validating oversized
  collections. Accept and reject outcomes are unchanged; an oversized array now reports only
  the size issue, without per-element issues.
- **serialize-javascript** is used only at build time by `@rollup/plugin-terser`, which declares
  `^7.0.3`. The lock entry alone was moved; no override is needed. 7.1.3 is the first patched
  release; 7.1.4 adds one further correction and was the latest age-eligible release.
- **vitest** is a development dependency. `@vitest/mocker` and the other packages of the same
  release move with it.

The npm lockfile changes only these packages. The Dependabot pull requests could not be merged
as they were: #110 and #99 refresh many unrelated packages to releases younger than the
release-age policy allows, so their frozen installs stop at the supply-chain check; #105 changes
`packages/schema/package.json` without the lockfile, so its frozen install fails on the
mismatch. None of them touches the Deno pin. This package replaces #110 and #105. No age
exemption is added.

## Advisories left open, and why

| Package   | Advisory                                                                          | Why it stays                                                                                                                                                                                                                     |
| --------- | --------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| minimatch | [GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249) (medium) | Advisory metadata lists 11.0.1 as the first patched release. The locked 10.2.6 comes from eslint, `@eslint/config-array`, `typescript-estree` and glob, which all declare `^10`. The locked 5.1.9 is outside the affected range. |
| glob      | [GHSA-3g3m-2fjr-6pw4](https://github.com/advisories/GHSA-3g3m-2fjr-6pw4) (medium) | Advisory metadata lists 14.0.2 as the first patched release. workbox-build declares `^11.0.1` and rimraf (Capacitor CLI) declares `^13.0.3`. A later 13.0.7 exists; whether it carries the fix was not evaluated.                |
| deepmerge | GHSA-gcqx-w48m-w2h4 (low)                                                         | GitHub lists the advisory as withdrawn with no patched release, and `pnpm audit` did not report it on 2026-11-16. 4.3.1 is the latest release.                                                                                   |

All three are reached only through build and lint tooling run on repository input. They were
not found in the three built web bundles or in `deno.lock`; the native Android and iOS bundles
were not inspected. Forcing a new major through an override was not tried here; that is a
separate package with its own build and native-CI evidence.

No production deployment, dependency-alert dismissal or security check waiver follows from this
package. The Edge Functions on the hosted service keep running whatever was last deployed until
a separately approved deployment. Read back alert state after merging rather than infer it from
a successful install.
