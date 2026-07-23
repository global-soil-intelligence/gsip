# Independent adversarial review — local proposal only

**Finding:** no demonstrated authorization or dispatch defect in proposal SHA-256 `f56380b5a479045d65fda8318ccaa51aa0910d6d837fb3f06ea620598b6d43e7`. It is suitable for a spec-first source change and CI review. It is not production authorization or a hosted zero-finding result.

The three private privileged function bodies are byte-for-byte equal to their original public bodies. The public names, parameter names/types and return types are retained. Existing public ACLs and owners were unchanged in the role-proof catalog comparison, which includes explicit grantees and grantability. The new private EXECUTE grants supply only the existing guarded operations to their existing caller roles; no schema USAGE or table grants are added.

This removes directly exposed definer implementations while retaining intentional, narrowly guarded public operations. It does not eliminate privileged execution behind those operations. This is consistent with [Supabase's private definer guidance](https://supabase.com/docs/guides/database/postgres/row-level-security); the security argument rests on the unchanged guards and caller rights, not a clean linter alone.

## Independent HTTP and lifecycle proof

I ran **33/33 checks** using immutable f9 source, cached PostgreSQL17.6 and PostgREST14.15, a network-none namespace shared by the two containers, no host ports and loopback-only container curl. Fixtures used `POINT EMPTY`, with no coordinate values, real data or actual photos. Signing material/JWTs existed only at runtime; response bodies were not persisted. Containers and the fixture directory were removed.

Receipt: `gate-c-security-remediation-http-local-proof-2026-10-12.json`, SHA-256 `1667c648580787a6dd79485a8e57f9973cb2472e42ba426e45429f938da53928`.

The checks covered owner/other-owner/anon/service/no-UID cases; required photo rows; idempotent finalization; live and withdrawn upload eligibility; GET/POST private schema profile rejection; same pooled backend with UID and role reset; private EXECUTE revocation defeating a warmed adapter; restore recovering without reload; private callee replacement changing the bound call result; dependency-blocked DROP; and two PostgREST schema-cache reloads. Capture remained closed.

The first harness attempt assumed a non-existent PostgreSQL binary path, failed before tests and cleaned up. The cached image's verified Nix PATH resolved it. Its failure receipt is retained as `gate-c-security-remediation-http-local-proof-attempt1-2026-10-12.json`.

## Namespace, dependency and race analysis

The local role proof demonstrates that client name resolution in private remains denied. This is not a universal namespace access boundary: [PostgreSQL privileges documentation](https://www.postgresql.org/docs/17/ddl-priv.html) explains that USAGE controls lookup and previously resolved references can remain usable. Narrow private EXECUTE and guards are therefore necessary, including for bound calls.

SQL-standard RETURN bodies bind their dependencies at definition time; [CREATE FUNCTION documentation](https://www.postgresql.org/docs/17/sql-createfunction.html) documents that distinction. The independent HTTP test confirms that replacing a private body is observed, ACL revocation is enforced, and ordinary DROP is rejected by a dependency. Use CREATE OR REPLACE to retain function identity; avoid DROP CASCADE and blind recreation in later migrations.

The finalization body retains its row lock and idempotence. The wrapper adds no new read/write step or guard outside that body. The RLS helpers still read as the private owner, so their original nonrecursive behavior remains. Existing262 pgTAP assertions passed before and after according to the separately inspected role-proof receipt; I did not independently rerun that entire suite.

The two restrictive false policies document intentional denial and remain denying even after local fault-injected SELECT grants. Service-role bypass behavior remains unchanged. This is actual access policy, not a suppressed finding.

## Required delivery and production checks

1. Deliver the migration atomically: creation, PUBLIC/default-role revocation and narrow regrant must not be separate production commits. The HTTP proof applied it in one local transaction. The standalone proposal is not an idempotent repair script; migration-ledger delivery must prevent blind reapplication.
2. Before production delivery, inspect safe function default-ACL metadata for the actual migration owner, globally and in private. Per-function revocation names PUBLIC/anon/authenticated/service_role; an unrelated custom default grantee would not be removed by that statement. Assert every new private function's complete ACL, including grantability, matches the reviewed allowlist after migration. Assert private function owner and RLS-bypass assumptions are the reviewed owner.
3. Confirm live exposed schemas and then reload the hosted schema cache after the approved commit. [PostgREST RPC guidance](https://docs.postgrest.org/en/v14/references/api/functions.html) requires cache refresh for function changes. A production read-only RPC check of capture_is_open and a private-profile rejection can confirm routing without contributor writes; valid owner/missing-shot/idempotent/withdrawn cases should remain local or use a separately authorized disposable staging target.
4. Fresh hosted security advisor must return zero. No waiver, ignore, RLS disabling or grant expansion is proposed.

The actual target's fresh Data API settings readback shows exposed `public` and `graphql_public`, with `private` excluded and Save disabled. Receipt: `production-data-api-exposed-schemas-ui-readonly-2026-10-12.json`, SHA-256 `96df3a2962089f32084ea47873b3f2aa44f2122ed9d7aa1682435a5418033a97`. No setting was changed. This readback closes the earlier runtime-configuration uncertainty for the observed target/time, while later drift still requires a fresh check.

Limitations: cached local PostgREST14.15 and a Supabase SQL stand-in do not prove every hosted Auth provider behavior or arbitrary concurrent DDL. The new narrow private default-ACL/owner check is a production preflight requirement, not a demonstrated current defect.

