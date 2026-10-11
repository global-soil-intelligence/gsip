// WP-AGENT-1: GSIP's public read interfaces for people and agents (REST + MCP), deployed with
// `verify_jwt = false`. It holds only the project's publishable key, so the anonymous role's
// grants and row-level security bound every read (SPEC I12). Request logic lives in
// packages/schema/src/agent/; this file is the adapter.
import { createPublicHandler } from '../../../packages/schema/src/agent/handler.ts'
import { publishableKeyFrom } from '../../../packages/schema/src/agent/keys.ts'
import { postgrestReader } from '../../../packages/schema/src/agent/reader.ts'

const url = Deno.env.get('SUPABASE_URL')?.replace(/\/+$/, '')
const publishableKey = publishableKeyFrom((name) => Deno.env.get(name))

/** A positive whole number from the environment, or undefined to use the default. */
function positive(name: string): number | undefined {
  const value = Number(Deno.env.get(name))
  return Number.isInteger(value) && value > 0 ? value : undefined
}

const handler =
  url && publishableKey
    ? createPublicHandler({
        reader: postgrestReader({ url, publishableKey }),
        datasetRepo: Deno.env.get('HF_DATASET_REPO') ?? undefined,
        // Answers embed this URL, so it never comes from request headers.
        publicBaseUrl:
          Deno.env.get('GSIP_PUBLIC_BASE_URL') ??
          `${url}/functions/v1/gsip-public`,
        rateLimitPerMinute: positive('GSIP_PUBLIC_RATE_LIMIT_PER_MINUTE'),
        instanceRateLimitPerMinute: positive(
          'GSIP_PUBLIC_INSTANCE_LIMIT_PER_MINUTE',
        ),
      })
    : null

// Unconfigured (no project URL or no publishable key): answer, but never read.
Deno.serve((request) =>
  handler
    ? handler(request)
    : new Response(JSON.stringify({ error: 'Service unavailable' }), {
        status: 503,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      }),
)
