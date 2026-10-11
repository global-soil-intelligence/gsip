# Global Soil Intelligence Project

GSIP is an open-source citizen-science project building a living global soil map with people and AI agents. A phone app (also a no-install web app) guides contributors through privacy-safe soil photography with a printable reference card. GSIP combines those observations with public soil-map priors and, later, open models to produce soil estimates with explicit uncertainty. Agents can read public cells, the protocol and dataset releases through a public API and an MCP server; see the [agent guide](docs/AGENTS.md).

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
