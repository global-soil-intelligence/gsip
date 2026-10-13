import {
  AgentInputError,
  type ApiConfig,
  getCell,
  getProtocol,
  getRelease,
  listCells,
} from './api.ts'
import { API_VERSION, DOCS_URL, envelope } from './envelope.ts'
import { json } from './http.ts'
import { openApiDocument } from './openapi.ts'
import { PublicReadUnavailable, type PublicReader } from './reader.ts'

export type RestDeps = ApiConfig & {
  reader: PublicReader
  /** Where this function answers, e.g. `https://<project>.supabase.co/functions/v1/gsip-public`. */
  baseUrl: string
}

const HOUR = 'public, max-age=3600'
const FIVE_MINUTES = 'public, max-age=300'

function cached(body: unknown, cacheControl: string): Response {
  return json(body, 200, { 'Cache-Control': cacheControl })
}

function safeDecode(value: string): string {
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

function fail(
  status: number,
  error: string,
  headers: Record<string, string> = {},
) {
  return json({ error }, status, headers)
}

/** GET /v1/... routes. `path` has the function prefix removed and starts with "/". */
export async function handleRest(
  request: Request,
  path: string,
  deps: RestDeps,
): Promise<Response> {
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    return fail(405, 'Method not allowed', { Allow: 'GET, HEAD, OPTIONS' })
  }
  const url = new URL(request.url)
  try {
    if (path === '/' || path === '/v1' || path === '/v1/') {
      return cached(
        envelope({
          api_version: API_VERSION,
          openapi: `${deps.baseUrl}/v1/openapi.json`,
          mcp: `${deps.baseUrl}/mcp`,
          endpoints: [
            `${deps.baseUrl}/v1/protocol`,
            `${deps.baseUrl}/v1/cells/{cell}`,
            `${deps.baseUrl}/v1/cells?within={cell}&limit=100`,
            `${deps.baseUrl}/v1/releases/latest`,
          ],
          docs: DOCS_URL,
        }),
        HOUR,
      )
    }
    if (path === '/v1/openapi.json') {
      return cached(openApiDocument(deps.baseUrl), HOUR)
    }
    if (path === '/v1/protocol') {
      return cached(envelope(getProtocol()), HOUR)
    }
    if (path === '/v1/releases/latest') {
      return cached(envelope(await getRelease(deps.reader, deps)), FIVE_MINUTES)
    }
    if (path === '/v1/cells') {
      const limit = url.searchParams.get('limit')
      return cached(
        envelope(
          await listCells(deps.reader, {
            within: url.searchParams.get('within') ?? undefined,
            limit: limit === null ? undefined : Number(limit),
            after: url.searchParams.get('after') ?? undefined,
          }),
        ),
        FIVE_MINUTES,
      )
    }
    const cell = /^\/v1\/cells\/([^/]+)$/.exec(path)
    if (cell) {
      return cached(
        envelope(await getCell(deps.reader, safeDecode(cell[1] ?? ''))),
        FIVE_MINUTES,
      )
    }
    return fail(404, 'Not found; see /v1/openapi.json')
  } catch (error) {
    if (error instanceof AgentInputError) return fail(400, error.message)
    if (error instanceof PublicReadUnavailable) {
      return fail(503, error.message, { 'Retry-After': '30' })
    }
    return fail(500, 'Internal error')
  }
}
