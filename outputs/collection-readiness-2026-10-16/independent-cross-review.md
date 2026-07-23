# Independent COLLECT-2 cross-review

Status: no open material findings on the source hashes recorded in `independent-cross-review.json`.

Reviewed the frozen frontend identity/rights flow, ordinary closed landing, explicit rights-only view, queue admission fences, export classification/publication refusal and separate invited build/receipt contract against the frozen pilot design. The six material findings listed in the JSON were fixed and re-read. In particular, an unused provisioned account is never falsely reported deleted, a committed server request remains confirmed when device cleanup fails, the pending warning survives intentional sign-out and resolves after a successful local retry, and old-owner My Soil results cannot survive an identity change. Pilot copy retains the private/publication and scientific limits.

Independently executed 96 tests in eight pilot/rights React files and 85 focused export/artifact Python tests: all passed. `git diff --check` passed. Root/frontend author owns broader CI and browser-matrix results; those are not claimed as independently run here.

This is source/local-test review, not production readiness, deployment approval, account provisioning, capture activation or evidence of real phone/hosted cleanup. This agent authored the DB implementation, so its DB verification is a separate receipt and requires the other independent reviewer. No canonical invited artifact was built or deployed by this review.
