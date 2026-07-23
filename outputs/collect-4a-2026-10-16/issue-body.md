WP-COLLECT-4A under SPEC v17 §5.2 and the live-camera design merged in #89. Justin's subsequent “go” authorizes the reviewed source-build sequence; production, Pages, capture, library uploads and actual-camera/device actions remain held.

Add a pure RAM-only guide-session contract and a narrow atomic queue handoff before any live camera UI. Preserve I1–I15, L1–L7, B1–B8, required A+B/optional C, real depth and explicit sample opt-in, owner/auth/rights/revision fences, existing queue/record formats and all default-closed artifacts.

Acceptance:

- Stable session/observation/shot intents; stale or mismatched owner/auth/revision work refused; held background selections require fresh same-context resume.
- Freeze an independent immutable pending queue snapshot and retain its identity through uncertain completion and its own successor revision.
- Atomically reconcile existing immutable identity before consumed-draft checks; preserve mutable sync progress. For new records require all persisted photo slots empty, exact owned optional library context, and advance the existing revision once. No blind overwrite or blanket cleanup.
- Original revision on existing photo/library writers; missing legacy revision holds for explicit discard/restart. Observable stale-save refusal reaches UI; no false ready/saved message or late restore/declaration resurrection.
- Meaningful failure-before/regression tests, independent review and required CI green. No camera preview/controller yet; no dependencies, native/config/store/version/backend-format/activation changes.

COLLECT-4B remains dependent on this package being reviewed, green and merged. No production or collection authority follows from a source/CI pass.
