## Problem and result

The draft privacy notice still left the map tile host undecided. WP-SITE-1E records Justin's conditional choice of repository-owned, same-origin GitHub Pages, updates the runbook and adds `docs/PRIOR_TILE_HOSTING.md`. ISRIC WMS remains the active fallback.

## Invariants and acceptance

- [x] Only SoilGrids-derived values enter prior archives; no contributor data or photos.
- [x] Tiles never enter git history; palette-version release assets are assembled into Pages at deploy time.
- [x] Tile target <=700 MB; complete site well below 1 GB; actual archive URLs must answer ranges with 206 and correct bytes.
- [x] No release, variable, host activation or Pages publication is authorized by destination approval.
- [x] Draft privacy-host disclosure and separate preparation/publication/activation evidence are documented.

## Verification

Six processor/privacy tests, targeted Ruff/mypy, terminology, changed-document Prettier and diff checks passed. New disclosure assertions failed without the update; ten local hosting links resolve. PR CI is pending.

Assumptions and limits: this is a documented hosting policy, not implemented release retrieval or asset assembly. No archives were built; size, byte-range support and published provenance remain unverified. Counsel approval of the legal pack and Justin's per-step publication go remain required.

## Authority and assumptions

- Justin Hart is product owner and human of record; Codex wrote this follow-up. Justin reviews and merges. No merge, approval, deployment or capture opening occurred.
- This PR starts from green WP-APP-1 head `f9e1ac2` and stays stacked there until the reviewed stack merges. Existing reviewed commits are preserved.
- Capture and production anonymous sign-in stay closed. I5, I7, I12 and B1–B8 remain binding. MIT code, ODbL 1.0 data and CC BY-SA 4.0 photos are unchanged. No dependency added.
