import type { ApiConfig } from './api.ts'
import { SERVER_NAME } from './envelope.ts'
import { CORS_HEADERS, empty, json } from './http.ts'
import { handleMcp } from './mcp.ts'
import { createRateLimiter, clientKey } from './rateLimit.ts'
import type { PublicReader } from './reader.ts'
import { handleRest } from './rest.ts'

export type PublicHandlerOptions = ApiConfig & {
  reader: PublicReader
  /** Requests per minute per client (GSIP_PUBLIC_RATE_LIMIT_PER_MINUTE, default 60). */
  rateLimitPerMinute?: number
  /**
   * Requests per minute for one function instance across all clients
   * (GSIP_PUBLIC_INSTANCE_LIMIT_PER_MINUTE, default 20 times the per-client limit). Client keys
   * come from headers a caller may be able to forge, so this ceiling is what bounds the load one
   * caller can put on the database.
   */
  instanceRateLimitPerMinute?: number
  /** This function's public URL; derived from the request URL when unset. */
  publicBaseUrl?: string
  now?: () => number
}

/** Removes the platform prefixes, so routes read the same locally and on Supabase. */
export function routePath(pathname: string): string {
  const path = pathname
    .replace(/^\/functions\/v1(?=\/|$)/, '')
    .replace(new RegExp(`^/${SERVER_NAME}(?=/|$)`), '')
  return path === '' ? '/' : path
}

function baseUrlFor(request: Request, configured: string | undefined): string {
  if (configured) return configured.replace(/\/+$/, '')
  // Never from X-Forwarded-Host or X-Forwarded-Proto: a caller can set those, and answers that
  // embed this URL are publicly cacheable.
  return `${new URL(request.url).origin}/functions/v1/${SERVER_NAME}`
}

function tooManyRequests(retryAfterSeconds: number): Response {
  return json({ error: 'Too many requests; slow down' }, 429, {
    'Retry-After': String(retryAfterSeconds),
  })
}

/**
 * The `gsip-public` request handler: REST under /v1 and MCP at /mcp, read-only and anonymous.
 * Pure Fetch API, so it runs in the Edge Function and in tests alike.
 */
export function createPublicHandler(
  options: PublicHandlerOptions,
): (request: Request) => Promise<Response> {
  const perClient = options.rateLimitPerMinute ?? 60
  const limitClient = createRateLimiter({
    perMinute: perClient,
    now: options.now,
  })
  const limitInstance = createRateLimiter({
    perMinute: options.instanceRateLimitPerMinute ?? perClient * 20,
    now: options.now,
    maxClients: 1,
  })
  return async (request) => {
    if (request.method === 'OPTIONS') return empty(204)
    const client = limitClient(clientKey(request))
    if (!client.allowed) return tooManyRequests(client.retryAfterSeconds)
    const instance = limitInstance('instance')
    if (!instance.allowed) return tooManyRequests(instance.retryAfterSeconds)
    const path = routePath(new URL(request.url).pathname)
    try {
      if (path === '/mcp') return await handleMcp(request, options)
      const response = await handleRest(request, path, {
        ...options,
        baseUrl: baseUrlFor(request, options.publicBaseUrl),
      })
      return request.method === 'HEAD'
        ? new Response(null, {
            status: response.status,
            headers: response.headers,
          })
        : response
    } catch {
      return json({ error: 'Internal error' }, 500, CORS_HEADERS)
    }
  }
}
