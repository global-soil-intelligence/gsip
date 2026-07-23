# Global Soil Intelligence Project

GSIP is an open-source citizen-science project for building a living global soil map. A shared web, iPhone, and Android app guides contributors through privacy-safe soil photography with a printable reference card. GSIP combines those observations with public soil-map priors and later open models to produce probabilistic soil estimates with explicit uncertainty.

GSIP is not a laboratory-test replacement. Public outputs use H3-resolution locations, never precise contributor coordinates. Photos are sanitized before canonical storage and checked again before public release.

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

## Mobile app

The app combines Explore, Capture, My observations, Learn, and Account. Field capture supports native camera and location access, saved drafts, and queued uploads. See [mobile build and test notes](docs/MOBILE_BUILD_AND_TEST.md) for local previews, platform builds, backend setup, and release limitations.

## Soil prediction research

Run `uv run python -m ml status` to see pilot readiness. The [prediction pilot guide](docs/PREDICTION_PILOT.md) explains how to link reviewed photos to laboratory results, train and compare soil-carbon baselines, and evaluate uncertainty. Research models stay on hold until evidence gates pass; the phone app does not yet display image-derived soil properties.

## Governing documents

- [Architecture specification](docs/SPEC.md)
- [Build order](docs/BUILD_ORDER.md)
- [Phase 1 deployment handoff](docs/PHASE1_DEPLOYMENT.md)
- [Archived v2.0 planning](docs/archive/v2.0/)

Code is MIT. Databases and structured data are ODbL 1.0. Contributed photos are CC BY-SA 4.0 with recorded contributor grants and pre-launch legal review.
