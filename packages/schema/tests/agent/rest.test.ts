import { describe, expect, it } from 'vitest'
import { createPublicHandler, routePath } from '../../src/agent/handler'
import { clientKey } from '../../src/agent/rateLimit'
import type { PublicReader } from '../../src/agent/reader'
import { PublicReadUnavailable } from '../../src/agent/reader'
import {
  BURLINGTON_R4,
  BURLINGTON_R6,
  BURLINGTON_R8,
  BURLINGTON_R9,
  ELSEWHERE_R8,
  EMPTY_R8,
  fakeReader,
  PUBLISHED,
  SIBLINGS_R8,
} from './fixtures'

const BASE = 'https://project.supabase.co/functions/v1/gsip-public'

function handler(reader: PublicReader = fakeReader(PUBLISHED), extra = {}) {
  return createPublicHandler({
    reader,
    datasetRepo: 'global-soil-intelligence/gsip',
    publicBaseUrl: BASE,
    ...extra,
  })
}

async function get(
  path: string,
  reader?: PublicReader,
  init: RequestInit = {},
) {
  const response = await handler(reader)(new Request(`${BASE}${path}`, init))
  const text = await response.text()
  return { body: text ? JSON.parse(text) : null, response }
}

describe('REST routes', () => {
  it('strips the platform prefixes so routes read the same everywhere', () => {
    expect(routePath('/functions/v1/gsip-public/v1/protocol')).toBe(
      '/v1/protocol',
    )
    expect(routePath('/gsip-public/v1/protocol')).toBe('/v1/protocol')
    expect(routePath('/gsip-public')).toBe('/')
    expect(routePath('/mcp')).toBe('/mcp')
  })

  it('serves the protocol with licence, attribution and citation', async () => {
    const { body, response } = await get('/v1/protocol')
    expect(response.status).toBe(200)
    expect(response.headers.get('cache-control')).toBe('public, max-age=3600')
    expect(response.headers.get('access-control-allow-origin')).toBe('*')
    expect(body.data.version).toBe('1.1')
    expect(body.data.shots.map((shot: { id: string }) => shot.id)).toEqual([
      'A',
      'B',
      'C',
    ])
    expect(body.license).toMatchObject({
      data: 'ODbL-1.0',
      photos: 'CC-BY-SA-4.0',
    })
    expect(body.attribution).toContain('GSIP')
    expect(body.citation.bibtex).toContain('@misc{gsip')
  })

  it('returns a published cell with the coarser published cells that contain it', async () => {
    const { body, response } = await get(
      `/v1/cells/${BURLINGTON_R8.toUpperCase()}`,
    )
    expect(response.status).toBe(200)
    expect(body.data).toEqual({
      cell: BURLINGTON_R8,
      resolution: 8,
      status: 'published',
      published: {
        cell: BURLINGTON_R8,
        resolution: 8,
        observations: 7,
        contributors: 4,
        gold_labels: 0,
        latest_observation_date: '2026-09-30',
      },
      containing: [
        expect.objectContaining({ cell: BURLINGTON_R6, resolution: 6 }),
        expect.objectContaining({ cell: BURLINGTON_R4, resolution: 4 }),
      ],
    })
  })

  it('answers withheld and empty cells alike, with only public containing cells', async () => {
    // BURLINGTON_R8's observations are withheld (its row is not published); EMPTY_R8 in the same
    // resolution-6 cell never had any. Apart from the cell asked about, the answers are identical.
    const reader = fakeReader(PUBLISHED.slice(1))
    const withheld = await get(`/v1/cells/${BURLINGTON_R8}`, reader)
    const empty = await get(`/v1/cells/${EMPTY_R8}`, reader)
    const exceptCell = (data: Record<string, unknown>) => ({
      ...data,
      cell: undefined,
    })
    expect(exceptCell(withheld.body.data)).toEqual(exceptCell(empty.body.data))
    expect(withheld.body.data.cell).not.toBe(empty.body.data.cell)
    expect(withheld.body.data.status).toBe('no_published_observations')
    expect(withheld.body.data.published).toBeNull()
  })

  it('accepts no question finer than what it publishes', async () => {
    // A resolution-9 cell could learn nothing a resolution-8 one does not; it would only tell
    // GSIP more about where the person asking is.
    const point = await get(`/v1/cells/${BURLINGTON_R9}`)
    expect(point.response.status).toBe(400)
    expect(point.body.error).toMatch(/resolution 8 or coarser/)
    expect(point.body.error).toMatch(/resolution-8 parent/)
    const coarse = await get(`/v1/cells/${BURLINGTON_R6}`)
    expect(coarse.response.status).toBe(200)
    expect(coarse.body.data).toMatchObject({
      resolution: 6,
      status: 'published',
    })
    expect(
      coarse.body.data.containing.map((cell: { cell: string }) => cell.cell),
    ).toEqual([BURLINGTON_R4])
  })

  it('refuses malformed cells', async () => {
    for (const bad of [
      'not-a-cell',
      '%E0%A4%A',
      'ffffffffffffff',
      `${BURLINGTON_R8}0`,
    ]) {
      const { body, response } = await get(`/v1/cells/${bad}`)
      expect(response.status).toBe(400)
      expect(body.error).toMatch(/H3 cell/)
    }
  })

  it('lists published cells inside an area, page by page', async () => {
    const first = await get(`/v1/cells?within=${BURLINGTON_R4}&limit=2`)
    expect(first.response.status).toBe(200)
    const all = [
      BURLINGTON_R4,
      BURLINGTON_R6,
      BURLINGTON_R8,
      ...SIBLINGS_R8,
    ].sort()
    expect(
      first.body.data.cells.map((cell: { cell: string }) => cell.cell),
    ).toEqual(all.slice(0, 2))
    let next: string | null = first.body.data.next
    const seen = [...first.body.data.cells]
    while (next) {
      const page = await get(
        `/v1/cells?within=${BURLINGTON_R4}&limit=2&after=${next}`,
      )
      seen.push(...page.body.data.cells)
      next = page.body.data.next
    }
    expect(seen.map((cell) => cell.cell)).toEqual(all)
    expect(seen.map((cell) => cell.cell)).not.toContain(ELSEWHERE_R8)
  })

  it('validates list parameters', async () => {
    for (const query of [
      'within=nope',
      `within=${BURLINGTON_R9}`,
      `within=${BURLINGTON_R4}&limit=0`,
      `within=${BURLINGTON_R4}&limit=501`,
      `within=${BURLINGTON_R4}&limit=2.5`,
      `within=${BURLINGTON_R4}&after=page-two`,
      '',
    ]) {
      const { response } = await get(`/v1/cells?${query}`)
      expect(response.status, query).toBe(400)
    }
  })

  it('points to the latest release and its exact Hugging Face revision', async () => {
    const { body } = await get('/v1/releases/latest')
    expect(body.data.release).toEqual({
      version: '2026-10-11',
      released_at: '2026-10-11T03:20:00+00:00',
      rows: 120,
      photos: 236,
      hf_revision: '0123456789abcdef0123456789abcdef01234567',
      dataset_url:
        'https://huggingface.co/datasets/global-soil-intelligence/gsip',
      revision_url:
        'https://huggingface.co/datasets/global-soil-intelligence/gsip/tree/0123456789abcdef0123456789abcdef01234567',
    })
    const none = await get('/v1/releases/latest', fakeReader(PUBLISHED, null))
    expect(none.body.data).toEqual({ release: null })
  })

  it('reports an unreachable database as temporarily unavailable', async () => {
    const failing: PublicReader = {
      cells: async () => {
        throw new PublicReadUnavailable()
      },
      cellsInRanges: async () => {
        throw new PublicReadUnavailable()
      },
      latestRelease: async () => {
        throw new PublicReadUnavailable()
      },
    }
    const { body, response } = await get(`/v1/cells/${BURLINGTON_R8}`, failing)
    expect(response.status).toBe(503)
    expect(response.headers.get('retry-after')).toBe('30')
    expect(body.error).toMatch(/temporarily unavailable/)
  })

  it('describes itself with OpenAPI 3.1', async () => {
    const { body } = await get('/v1/openapi.json')
    expect(body.openapi).toBe('3.1.0')
    expect(body.servers).toEqual([{ url: BASE }])
    expect(Object.keys(body.paths)).toEqual([
      '/v1/protocol',
      '/v1/cells/{cell}',
      '/v1/cells',
      '/v1/releases/latest',
    ])
    expect(body.components.schemas.CellResponse.properties.data).toBeDefined()
  })

  it('answers HEAD without a body, refuses writes and unknown paths', async () => {
    const head = await handler()(
      new Request(`${BASE}/v1/protocol`, { method: 'HEAD' }),
    )
    expect(head.status).toBe(200)
    expect(await head.text()).toBe('')
    expect(
      (await get('/v1/protocol', undefined, { method: 'DELETE' })).response
        .status,
    ).toBe(405)
    expect((await get('/v1/unknown')).response.status).toBe(404)
    const preflight = await handler()(
      new Request(`${BASE}/mcp`, { method: 'OPTIONS' }),
    )
    expect(preflight.status).toBe(204)
    expect(preflight.headers.get('access-control-allow-headers')).toContain(
      'mcp-protocol-version',
    )
  })

  it('limits each client, best effort, and tells it when to come back', async () => {
    let now = 0
    const limited = createPublicHandler({
      reader: fakeReader(PUBLISHED),
      publicBaseUrl: BASE,
      rateLimitPerMinute: 2,
      now: () => now,
    })
    const call = (ip: string) =>
      limited(
        new Request(`${BASE}/v1/protocol`, {
          headers: { 'x-forwarded-for': ip },
        }),
      )
    expect((await call('203.0.113.7')).status).toBe(200)
    expect((await call('203.0.113.7')).status).toBe(200)
    const refused = await call('203.0.113.7')
    expect(refused.status).toBe(429)
    expect(Number(refused.headers.get('retry-after'))).toBeGreaterThan(0)
    expect((await call('198.51.100.4')).status).toBe(200)
    now += 30_000
    expect((await call('203.0.113.7')).status).toBe(200)
  })

  it('keys clients by the edge address, and caps one instance whatever the headers say', async () => {
    const limited = createPublicHandler({
      reader: fakeReader(PUBLISHED),
      publicBaseUrl: BASE,
      rateLimitPerMinute: 2,
      instanceRateLimitPerMinute: 5,
      now: () => 0,
    })
    const call = (headers: Record<string, string>) =>
      limited(new Request(`${BASE}/v1/protocol`, { headers }))
    // A forged X-Forwarded-For does not buy a fresh allowance when the edge reports the address.
    expect(
      (
        await call({
          'cf-connecting-ip': '203.0.113.7',
          'x-forwarded-for': '10.0.0.1',
        })
      ).status,
    ).toBe(200)
    expect(
      (
        await call({
          'cf-connecting-ip': '203.0.113.7',
          'x-forwarded-for': '10.0.0.2',
        })
      ).status,
    ).toBe(200)
    expect(
      (
        await call({
          'cf-connecting-ip': '203.0.113.7',
          'x-forwarded-for': '10.0.0.3',
        })
      ).status,
    ).toBe(429)
    // Rotating forged addresses runs into the instance ceiling (5 a minute here).
    const statuses = []
    for (let n = 4; n <= 8; n++) {
      statuses.push((await call({ 'x-forwarded-for': `10.0.0.${n}` })).status)
    }
    expect(statuses).toEqual([200, 200, 200, 429, 429])
  })

  it('bounds the memory a forged address can take', () => {
    const key = clientKey(
      new Request(BASE, { headers: { 'x-forwarded-for': 'a'.repeat(4096) } }),
    )
    expect(key.length).toBeLessThanOrEqual(64)
    expect(clientKey(new Request(BASE))).toBe('unknown')
  })

  it('never builds its own URLs from forwarded headers', async () => {
    const unconfigured = createPublicHandler({ reader: fakeReader(PUBLISHED) })
    const response = await unconfigured(
      new Request(`${BASE}/v1`, {
        headers: {
          'x-forwarded-host': 'attacker.example',
          'x-forwarded-proto': 'http',
        },
      }),
    )
    const text = await response.text()
    expect(text).not.toContain('attacker.example')
    expect(JSON.parse(text).data.openapi).toBe(`${BASE}/v1/openapi.json`)
  })
})
