// WP-AGENT-1: GSIP's public read interfaces for people and agents (REST + MCP), deployed with
// `verify_jwt = false`. It holds only the project's publishable key, so the anonymous role's
// grants and row-level security bound every read (SPEC I12). Request logic and configuration live
// in packages/schema/src/agent/; this file is the adapter.
import { publicFunctionConfig } from '../../../packages/schema/src/agent/config.ts'
import { createPublicHandler } from '../../../packages/schema/src/agent/handler.ts'
import { postgrestReader } from '../../../packages/schema/src/agent/reader.ts'

function createHandler() {
  const config = publicFunctionConfig((name) => Deno.env.get(name))
  if (!config) return null
  const { url, publishableKey, ...options } = config
  return createPublicHandler({
    ...options,
    reader: postgrestReader({ url, publishableKey }),
  })
}

const handler = createHandler()

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
