# Changelog

Software releases of GSIP. Data and photo releases are separate, gated, and not listed here.

## v0.1.0 — 2026-11-16 (pre-release)

The first tagged snapshot of the source. It is a reference point for builders and for citation.
It is not a launch: hosted capture is closed, no soil-property estimator exists, and nothing here
has been validated in the field.

What the source contains at this tag:

- **Capture app** for phone browsers, with an offline queue and an optional browser camera
  framing guide (invited-pilot path only, tested with synthetic media). A Capacitor configuration
  lets CI generate unsigned Android and iOS test builds. There is no store release, and iOS
  private storage is unresolved. Hosted capture is closed.
- **Backend** source for Supabase: schema, row-level security, Edge Functions, a public read API
  and an MCP server for agents.
- **Pipeline:** photo sanitising and QA, export and tile workers, and photo privacy screening and
  review worker source (not calibrated, not deployed; no photo publication).
- **Reference cards:** a printable A6 card and a credit-card-size node card, with detectors.
  Photo QA finds either card and fits a per-photo colour normalisation for a future estimator.
  This is tested on generated photos only and is not calibration.
- **Soil library tools:** private local node store, intake and exchange contracts, and a
  synthetic demo.
- **Specification v18** (proposed; §17 is not yet adopted by the owner) and the build order,
  which record what is built, what is proposed and what is gated.

Nothing in this list is a statement about what is deployed or hosted.

Known limits at this tag:

- No printed card or phone photo has been used to test the card code.
- Uneven light between card and soil is not reliably caught
  ([#114](https://github.com/global-soil-intelligence/gsip/issues/114)).
- Two open dependency advisories in build tooling, and one withdrawn, are left in place, with
  reasons in [DEPENDENCY_REMEDIATION.md](docs/DEPENDENCY_REMEDIATION.md).
- No Zenodo record or DOI.
