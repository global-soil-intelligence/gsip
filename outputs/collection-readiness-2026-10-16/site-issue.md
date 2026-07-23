## WP-SITE-1H — Honest closed-capture status

The public capture page says both that contributions are closed and that it is ready for a first observation. Its closed-page paragraph also wrongly singles out legal review as the reason collection has not opened.

Invariants: retain the exact existing activation behavior, absent upload controls in closed builds, live capture status behavior, privacy, licences and every production/publication gate. No workflow, schema or dependency changes.

Change the closed card to describe a collection service still being prepared. Its status must say collection is closed for unset/false build flags, while a live build retains the existing first-observation status. Add a regression that fails on the current contradiction and verify the existing tests, build, Pages closed-artifact checks and budgets. Link SPEC v14's collection readiness, but this copy fix itself grants no activation authority.

No merge, deployment, account change, worker dispatch or capture/library opening is authorized.
