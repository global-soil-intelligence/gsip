# Global Soil Intelligence Project

GSIP is building an **open soil spectral reference library**, with smartphones as the accessible capture and sample-linking tool. The library connects camera observations and metadata to instrument spectra and verified laboratory evidence; open AI models and the soil map are downstream goals. Ordinary RGB phone photos are optical observations, not wavelength-resolved spectra. See the [library specification](docs/SPEC.md#16-open-soil-spectral-library-v5-foundation-v6v7-private-intake) and [implementation sequence](docs/BUILD_ORDER.md#library-first-implementation-sequence-spec-16).

The collection foundation includes a phone app and a no-install web app for guided, privacy-safe soil photography with a printable reference card. The current map supplies public soil-map priors; later evaluated library models will supply estimates with explicit uncertainty. Agents can read public cells, the protocol and dataset releases through a public API and an MCP server; see the [agent guide](docs/AGENTS.md).

GSIP is not a laboratory replacement. Public outputs locate observations by k-anonymous H3 cells, never precise coordinates. Photos are sanitized before canonical storage and checked again before release.

## Build on GSIP

**The whole GSIP software stack is open source.** The public repository contains the apps,
backend, data pipeline, library tools, modelling code, API, reference-card generator and tests.
You can use, fork, modify, self-host and extend the software under MIT, including in your own
products. You can also build on one component without running the whole service.
Documentation is CC BY 4.0; released structured data is ODbL 1.0 and contributed photos are
CC BY-SA 4.0. Third-party dependencies and model artifacts retain their own licences.

“Private local node” means that your records and credentials stay under your control. The node
software itself is public. GSIP’s hosted-service and publication approvals protect contributors;
they do not add restrictions to the open-source software licence. Names and marks remain
separate under [TRADEMARKS.md](TRADEMARKS.md).

| Build with                                           | Public source and starting point                                                                  |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| Phone and web capture app                            | [`apps/capture-pwa/`](apps/capture-pwa/) · [app build guide](docs/APP_STORE.md)                   |
| Soil map and public website                          | [`apps/map-web/`](apps/map-web/) · [`apps/site-web/`](apps/site-web/)                             |
| Library store, optical extraction and synthetic demo | [`pipeline/`](pipeline/) · [library developer guide](docs/SOIL_LIBRARY.md)                        |
| Modelling and evaluation baseline                    | [`ml/`](ml/) · [synthetic demo and its limits](docs/SOIL_LIBRARY.md#run-the-complete-local-demo)  |
| Shared schemas and exchange contracts                | [`packages/schema/`](packages/schema/) · [node exchange contract](docs/NODE_EXCHANGE_CONTRACT.md) |
| Database, security policies and Edge Functions       | [`supabase/`](supabase/) · [local database commands](supabase/README.md)                          |
| QA, rights, export and tile workers                  | [`pipeline/`](pipeline/) · [deployment runbook](docs/PHASE1_DEPLOYMENT.md)                        |
| Public REST API and MCP server                       | [`packages/schema/src/agent/`](packages/schema/src/agent/) · [agent guide](docs/AGENTS.md)        |
| Printable reference card                             | [`card/`](card/)                                                                                  |
| Tests and build workflows                            | [`tests/`](tests/) · [`.github/workflows/`](.github/workflows/)                                   |

The implemented source and tests are available now, including development branches and pull
requests. Public source is not a promise that every planned feature is complete: real peer
exchange, verified field adapters, independently validated field models and public spectral
releases remain scheduled/gated work. The iOS storage prototype is public in [draft #73](https://github.com/global-soil-intelligence/gsip/pull/73)
and remains held on its native CI/device requirements. See [BUILD_ORDER](docs/BUILD_ORDER.md)
for acceptance criteria. Public capture and hosted library uploads remain closed.

## Start locally

Requirements: Node 24+, pnpm 11.9.0, Python 3.11–3.13, and uv. The library CLI and synthetic
demo need no GSIP account or production credential; follow the [library guide](docs/SOIL_LIBRARY.md)
to choose private output directories and run them.

```sh
git clone https://github.com/global-soil-intelligence/gsip.git
cd gsip
cp .env.example .env
pnpm install --frozen-lockfile
uv sync --frozen --all-groups
pnpm build
pnpm test
```

Keep both activation flags in `.env` false. The example values are placeholders; no production
secret is needed to build the source. Start the public site with
`pnpm --filter @gsip/site-web dev`, the closed capture app with
`pnpm --filter @gsip/capture-pwa dev`, or the map with
`pnpm --filter @gsip/map-web dev`. Live backend reads require your own configured instance.

Additional checks have separate tooling requirements: Docker plus the local Supabase CLI stack
for database checks; GDAL for the full tile tests; and Android SDK/Xcode for native builds.
See [CONTRIBUTING.md](CONTRIBUTING.md), [AGENTS.md](AGENTS.md) and the
[app build guide](docs/APP_STORE.md). Store signing and accounts are separate from source access.
Use the [deployment runbook](docs/PHASE1_DEPLOYMENT.md) when preparing an instance under your
own operator authority; it does not authorize changes to GSIP’s canonical production service.

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
