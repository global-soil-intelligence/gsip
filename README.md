# Global Soil Intelligence Project

GSIP is building an **open soil spectral reference library**, with smartphones as the accessible capture and sample-linking tool. The library connects camera observations and metadata to instrument spectra and verified laboratory evidence; open AI models and the soil map are downstream goals. Ordinary RGB phone photos are optical observations, not wavelength-resolved spectra. See the [library specification](docs/SPEC.md#16-open-soil-spectral-library-v5-foundation-v6v7-private-intake) and [implementation sequence](docs/BUILD_ORDER.md#library-first-implementation-sequence-spec-16).

The existing collection foundation is a phone app (also a no-install web app) guides contributors through privacy-safe soil photography with a printable reference card. The current map supplies public soil-map priors; later evaluated library models will supply estimates with explicit uncertainty. Agents can read public cells, the protocol and dataset releases through a public API and an MCP server; see the [agent guide](docs/AGENTS.md).

GSIP is not a laboratory replacement. Public outputs locate observations by k-anonymous H3 cells, never precise coordinates. Photos are sanitized before canonical storage and checked again before release.

## Start locally

Requirements: Node 24+, pnpm 11, Python 3.11-3.13, and uv.

```sh
cp .env.example .env
pnpm install
uv sync
pnpm build
pnpm test
uv run pytest
```

Run `pnpm --filter @gsip/capture-pwa dev` for capture or
`pnpm --filter @gsip/map-web dev` for the map.

For the private soil-library record contract and local node commands, see the
[soil library developer guide](docs/SOIL_LIBRARY.md). Private intake and compatible
phone integration have merged source, including [LIB-4C (#51)](https://github.com/global-soil-intelligence/gsip/pull/51).
The [LIB-5A exchange contract (#58)](https://github.com/global-soil-intelligence/gsip/pull/58)
and [LIB-5B synthetic local simulator (#64)](https://github.com/global-soil-intelligence/gsip/pull/64)
are also merged. Hosted deployment and activation, real peer sharing and scientific
model validation remain gated; these tools do not open capture.

Source for opt-in local sync reminders is merged in [APP-2B (#63)](https://github.com/global-soil-intelligence/gsip/pull/63).
The device, backup, store, legal and production gates remain separate from source completion.

## Governing documents

- [Architecture specification](docs/SPEC.md)
- [Build order](docs/BUILD_ORDER.md)
- [Agent guide](docs/AGENTS.md)
- [Governance and business guardrails](GOVERNANCE.md)
- [Phase 1 deployment handoff](docs/PHASE1_DEPLOYMENT.md)
- [Archived planning](docs/archive/)

Code is MIT. Databases and structured data are ODbL 1.0. Contributed photos are CC BY-SA 4.0 with recorded contributor grants and pre-launch legal review. Names and marks are covered by [TRADEMARKS.md](TRADEMARKS.md).

## Contributing and security

See [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow, DCO sign-off and rules for agent-written contributions. Report vulnerabilities privately using [SECURITY.md](SECURITY.md).

## Software and documentation licenses

Software is MIT (see [LICENSE](LICENSE)). Documentation terms are recorded in [DOCUMENTATION_LICENSE.md](DOCUMENTATION_LICENSE.md).
