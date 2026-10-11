/** Response helpers shared by the REST and MCP interfaces of `gsip-public`. */

export const CORS_HEADERS: Readonly<Record<string, string>> = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, HEAD, POST, OPTIONS',
  'Access-Control-Allow-Headers':
    'accept, apikey, authorization, content-type, mcp-method, mcp-name, mcp-protocol-version, x-client-info',
  'Access-Control-Expose-Headers': 'retry-after',
  'Access-Control-Max-Age': '86400',
}

export const NO_STORE = 'no-store'

export function json(
  body: unknown,
  status = 200,
  headers: Record<string, string> = {},
): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      ...CORS_HEADERS,
      'Cache-Control': NO_STORE,
      'Content-Type': 'application/json; charset=utf-8',
      'X-Content-Type-Options': 'nosniff',
      ...headers,
    },
  })
}

export function empty(
  status: number,
  headers: Record<string, string> = {},
): Response {
  return new Response(null, {
    status,
    headers: { ...CORS_HEADERS, 'Cache-Control': NO_STORE, ...headers },
  })
}
