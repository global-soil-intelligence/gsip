# GSIP data foundation

The migrations are the canonical database history and rebuild the complete v2.2 schema, RLS policies, and private Storage buckets. Never edit hosted tables outside a migration.

```sh
pnpm db:start
pnpm db:reset
pnpm db:test
pnpm db:stop
```

Anonymous contributors use Supabase Anonymous Sign-Ins, so they receive a unique `auth.uid()` and the `authenticated` database role. The public `anon` role can read only the H3-safe view and aggregate cells. Service-role credentials are server-only and must never be included in a browser bundle.

The seed is deterministic and idempotent. It creates 25 synthetic submissions across five continents; it contains no production identities or photo binaries.
