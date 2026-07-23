# Gate C security advisor audit — prepared only

Target: `toxldjgwkxtneoqsazym`. Edge deployment remains blocked; no Edge approval request or deployment was made. The existing plan, commands and smoke inputs retain their recorded SHA-256 values. See `edge-next-local-blocked-status-2026-10-12.json`.

The hosted receipt contains **7 finding instances on 6 distinct objects**, in 3 categories: two RLS-enabled/no-policy tables; one anonymous definer-function finding; four authenticated definer-function findings. `capture_is_open()` occurs in both function categories.

## Official rule semantics

The pinned official [Splinter source](https://github.com/supabase/splinter/blob/fccca4b1c4d8b48b8ccd69bd6b30e84adcb92975/splinter.sql) is archived locally, with its commit and file hashes in `official-splinter-source-receipt-2026-10-12.json`.

- 0028/0029 test definer status, effective role EXECUTE and schemas from `pgrst.db_schemas`, defaulting to `public`. These rules are not universally public-only and do not require GraphQL.
- 0008 identifies user regular tables with RLS and no policy, excluding managed schemas/extensions. It does not use that exposed-schema filter.
- The official [0008 guidance](https://github.com/supabase/splinter/blob/fccca4b1c4d8b48b8ccd69bd6b30e84adcb92975/docs/0008_rls_enabled_no_policy.md) recommends an explicit rejection policy when no ordinary access is intentional.

Authorized metadata-only SQL returned session `pgrst.db_schemas = NULL`, and no matching authenticator database or role settings. The inspected SQL session therefore uses the linter's default `public`. This proves no inspected DB/role override; it does **not** establish every runtime Data API configuration source. Receipt: `production-api-schema-metadata-readonly-2026-10-12.json`.

## GSIP contract audit and candidate remediation

These are proposals, not implemented or verified by this audit.

| Finding object | Existing contract and smallest candidate |
| --- | --- |
| `public.capture_is_open()` | Used in capture RLS and allowed to anon/authenticated/service_role. A direct invoker body can read the already granted `capture_open` column. Do not retain a predicate on `singleton`, whose SELECT privilege is not granted to ordinary callers. The constrained single-row table makes that extra read unnecessary. Preserve closed-on-empty behavior. |
| `public.current_auth_user_exists()` | Contributor-insert RLS denies creation from a deleted user's still-valid token. Retain the `auth.uid()` existence check in a private guarded definer body and preserve its public invoker signature if using an adapter. Do not grant users access to `auth.users`. |
| `public.my_submission_accepts_uploads(text)` | Storage RLS checks the caller's own submission and unwithdrawn grant. Preserve both checks inside the private privileged body; preserve the public adapter or update every dependent policy through a reviewed migration. |
| `public.finalize_submission(uuid)` | The capture client calls this RPC directly in `apps/capture-pwa/src/supabase.ts:311`. Its public name, parameter and timestamp return must remain compatible. The privileged body must retain null-user refusal, owner binding, row lock, required A/B photo rows and idempotence. |
| `public.grant_withdrawals`, `public.attribution_reviews` | RLS is already enabled, ordinary grants revoked, service grants intentional. Export and review workers use these public REST table routes. Explicit restrictive false policies can document/enforce denial while preserving service access and existing names. Moving tables private would also require worker/API changes. |

No inspected caller requires a public function's implementation to be definer; it requires the name/signature/behavior. [Supabase RLS guidance](https://supabase.com/docs/guides/database/postgres/row-level-security) recommends keeping definers outside exposed schemas, and [its helper guidance](https://supabase.com/docs/guides/troubleshooting/do-i-need-to-expose-security-definer-functions-in-row-level-security-policies-iI0uOw) says schema-qualified policy helpers need not be exposed.

A public invoker adapter does not confer owner privileges on its caller. The private body needs the caller's EXECUTE permission and must enforce authorization itself. The existing denial of private-schema USAGE should remain. A runtime-string SQL adapter can require schema resolution at execution; a SQL-standard RETURN body is parsed/bound when created, according to [PostgreSQL CREATE FUNCTION](https://www.postgresql.org/docs/17/sql-createfunction.html). Whether that avoids any new USAGE grant in this design must be established by local role proof, not assumed.

[Supabase function security guidance](https://supabase.com/docs/guides/database/functions) requires safe search paths, narrow execution grants and ownership checks within privileged functions. A private schema by itself is not an authorization boundary against already-bound calls.

## Required proof before advancing

Run the exact pinned 0008/0028/0029 predicates locally before and after remediation, with the configured exposed-schema list explicit; demonstrate the original failures first. Preserve all existing pgTAP tests. Exercise anon, current owner, another authenticated owner, deleted-user token, service_role, missing shots, withdrawn grants, and closed capture through actual RLS/RPC paths. Check public signatures/ACLs, private-schema USAGE denial and private function EXECUTE allowlists, unchanged table grants, private denial policies, and service worker access. Do not infer authorization from catalog flags alone.

Local tests cannot establish the hosted advisor result. A reviewed migration, migration-preservation test, separate production Go and fresh zero-finding hosted advisor receipt are needed before seeking Edge deployment approval. No ignore/suppression, RLS disabling or new table grants are proposed.

Limitations: this audit performed source/catalog-metadata reads only. It did not implement remediation, run the candidate role proof, run a new test suite, reconfigure Data API schemas, or mutate production.

