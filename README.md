# Global Soil Intelligence Project

GSIP is an open-source citizen-science project for building a living global soil map. Contributors use a phone-friendly web app to submit geotagged soil photos captured with a printable reference card. GSIP combines those observations with public soil-map priors and, in later phases, openly released models to produce probabilistic soil estimates with explicit uncertainty.

GSIP is not a laboratory-test replacement. Public outputs use H3-resolution locations, never precise contributor coordinates. Photo metadata is sanitized before canonical storage and checked again before public release.

## Status

Architecture v2.1 is approved for implementation; application code has not started. The next milestone is **WP-0: repository bootstrap**.

## Governing documents

- [Architecture specification](docs/SPEC.md) — mission, invariants, system design, data model, privacy, licensing, and roadmap.
- [Build order](docs/BUILD_ORDER.md) — guardrails, work packages, acceptance criteria, review gates, and sequencing.
- [Archived v2.0 planning](docs/archive/v2.0/) — retained for provenance only; do not implement.

## Project rules

- Code: MIT.
- Databases and structured data: ODbL 1.0.
- Contributed photos: CC BY-SA 4.0, subject to recorded contributor terms and pre-launch legal review.
- TypeScript and Python only.
- One work package per pull request; protected `main`; DCO sign-off required.

The public-launch gate is an end-to-end test in which a new contributor submits from a phone in under three minutes and sees only the fuzzed H3 cell on the map.
