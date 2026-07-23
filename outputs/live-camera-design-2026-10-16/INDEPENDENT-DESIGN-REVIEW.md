# Independent design review — 2026-10-16

Exact committed head: a45924b141740c58f8d3a3e3f023a0cf5cc6e8d4, PR #89.

Two read-only reviewers checked the actual five-file design against the existing camera, App, queue and library contracts. No reviewer edited files or invoked cameras or production.

1. Media/geometry review: full-frame geometry, SVG pixel exclusion, one unresolved request/encoder, resource arithmetic, late disposal and proposal-only authority. Required correction: acknowledge browser colour conversion/lossy JPEG rather than implying raw colour preservation. Corrected and reread clear.
2. State/ownership review: unowned picker draft isolation, owner/auth/revision races, exact optional library context, held background photos and atomic queue behavior. Required correction: prevent late writers restoring consumed IDs; every new guide commit advances the existing revision. Shared writer fixes are explicit future scope: hold missing/ambiguous revisions, preserve operation revision, expose refusal, require fresh retry. Outcome reconciliation precedes original-session/consumed-draft checks and preserves pending identity across its own successor revision. Focus/auth callbacks share the guide's one outstanding refresh. Corrected and reread clear.

Final state/ownership reviewer verified local HEAD and clean worktree at the exact commit above: no open findings; 36 prospective guards passed.

Limitations: these are specification/source reviews and prospective scope guards. No runtime camera implementation, actual IndexedDB race execution, phone/device qualification, production readiness or scientific accuracy is established. All such implementation/qualification/production gates remain separate.
