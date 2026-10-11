import { describe, expect, it } from 'vitest'
import soilGrids from './fixtures/soilgrids.json'
import urbanSoilGrids from './fixtures/soilgrids-urban.json'
import ssurgo from './fixtures/ssurgo.json'
import { priorLookupPoint, UpstreamError } from '../src/prior'
import {
  type BeginResult,
  type CachedEntry,
  DEFAULT_PRIOR_JOB_CONFIG,
  isServiceRequest,
  PRIOR_OUTCOME_HTTP_STATUS,
  type PriorJobDeps,
  runPriorJob,
  type StaticSource,
  type TokenCosts,
  type UpstreamBucket,
} from '../src/priorJob'

const IOWA = {
  capturedAt: '2026-10-08T15:00:00Z',
  id: 'submission-iowa',
  latitude: 41.9483,
  longitude: -93.625,
}
const KENYA = {
  capturedAt: '2026-10-08T15:00:00Z',
  id: 'submission-kenya',
  latitude: -0.3031,
  longitude: 36.08,
}
const NOW = new Date('2026-10-10T00:00:00Z')

const precipitation = {
  hourly: {
    precipitation: [2, 0],
    time: ['2026-10-07T10:00', '2026-10-08T10:00'],
  },
}

type Harness = {
  begins: Array<{ costs: TokenCosts; id: string; owner: boolean }>
  bodies: string[]
  cache: Map<string, CachedEntry>
  deps: PriorJobDeps
  enrichment: Array<Record<string, unknown>>
  finished: Array<Record<string, unknown>>
  priors: unknown[][]
  requests: string[]
  tokens: Map<UpstreamBucket, number>
}

/** Mirrors begin_prior_attempt: claimability first, then all-or-nothing token spending. */
function harness(
  options: {
    claimable?: boolean
    failing?: Array<string | [string, number]>
    soil?: unknown
    tokens?: Partial<Record<UpstreamBucket, number>>
  } = {},
): Harness {
  const state: Omit<Harness, 'deps'> = {
    begins: [],
    bodies: [],
    cache: new Map(),
    enrichment: [],
    finished: [],
    priors: [],
    requests: [],
    tokens: new Map<UpstreamBucket, number>([
      ['soilgrids', options.tokens?.soilgrids ?? 1],
      ['ssurgo', options.tokens?.ssurgo ?? 30],
      ['open_meteo', options.tokens?.open_meteo ?? 60],
    ]),
  }
  const deps: PriorJobDeps = {
    begin: async (id, owner, costs): Promise<BeginResult> => {
      state.begins.push({ costs, id, owner })
      if (options.claimable === false) return { outcome: 'not_claimable' }
      const entries = Object.entries(costs) as Array<[UpstreamBucket, number]>
      if (
        entries.some(([bucket, cost]) => (state.tokens.get(bucket) ?? 0) < cost)
      )
        return { outcome: 'deferred', retryAfterSeconds: 12 }
      for (const [bucket, cost] of entries)
        state.tokens.set(bucket, (state.tokens.get(bucket) ?? 0) - cost)
      return { attempts: 1, outcome: 'claimed' }
    },
    fetchJson: async (url, init) => {
      state.requests.push(url)
      if (typeof init.body === 'string') state.bodies.push(init.body)
      for (const failure of options.failing ?? []) {
        const [fragment, status] =
          typeof failure === 'string' ? [failure, 503] : failure
        if (url.includes(fragment))
          throw new UpstreamError(`status ${status}`, status)
      }
      const host = new URL(url).host
      if (host === 'rest.isric.org') return options.soil ?? soilGrids
      if (host === 'sdmdataaccess.sc.egov.usda.gov') return ssurgo
      if (url.includes('/v1/elevation')) return { elevation: [305] }
      return precipitation
    },
    finish: async (update) => {
      state.finished.push(update)
    },
    now: () => NOW,
    readCache: async (cell) => {
      const entries: Partial<Record<StaticSource, CachedEntry>> = {}
      for (const source of ['soilgrids', 'ssurgo', 'elevation'] as const) {
        const entry = state.cache.get(`${cell}:${source}`)
        if (entry) entries[source] = entry
      }
      return entries
    },
    writeCache: async (cell, source, payload) => {
      state.cache.set(`${cell}:${source}`, {
        payload,
        retrievedAt: NOW.toISOString(),
      })
    },
    writeEnrichment: async (enrichment) => {
      state.enrichment.push(enrichment)
    },
    writePriors: async (rows) => {
      state.priors.push(rows)
    },
  }
  return { ...state, deps }
}

describe('prior jobs', () => {
  it('enriches a CONUS submission from every source at the r9 cell centre', async () => {
    const h = harness()
    const outcome = await runPriorJob(h.deps, IOWA, false)
    expect(outcome).toMatchObject({
      emptySources: [],
      failedSources: [],
      priors: 28,
      status: 'completed',
    })
    expect(h.begins[0].costs).toEqual({
      open_meteo: 2,
      soilgrids: 1,
      ssurgo: 1,
    })
    expect(h.requests).toHaveLength(4)
    const point = priorLookupPoint(IOWA.latitude, IOWA.longitude)
    expect(point.latitude).not.toBe(IOWA.latitude)
    for (const request of h.requests) {
      const params = new URL(request).searchParams
      const latitude = params.get('lat') ?? params.get('latitude')
      const longitude = params.get('lon') ?? params.get('longitude')
      if (latitude === null) continue // SSURGO posts its point in the body
      expect(Number(latitude)).toBe(point.latitude)
      expect(Number(longitude)).toBe(point.longitude)
    }
    // The SSURGO call site sends the cell centre too, never the precise point.
    expect(h.bodies).toHaveLength(1)
    expect(h.bodies[0]).toContain(`POINT(${point.longitude} ${point.latitude})`)
    expect(h.bodies[0]).not.toContain(
      `POINT(${IOWA.longitude} ${IOWA.latitude})`,
    )
    expect(h.enrichment).toEqual([{ elevation: 305, precip_flag: true }])
    expect(h.finished).toEqual([
      { attempts: 1, emptySources: [], lastError: null, status: 'completed' },
    ])
  })

  it('serves a second submission in the same cell from the cache', async () => {
    const h = harness()
    await runPriorJob(h.deps, IOWA, false)
    h.requests.length = 0
    const outcome = await runPriorJob(
      h.deps,
      { ...IOWA, id: 'submission-iowa-2' },
      false,
    )
    expect(outcome.status).toBe('completed')
    // Only the capture-specific precipitation window is paid for and fetched again.
    expect(h.begins[1].costs).toEqual({ open_meteo: 1 })
    expect(h.requests).toHaveLength(1)
    expect(h.requests[0]).toContain('hourly=precipitation')
  })

  it('ignores cache entries older than the TTL', async () => {
    const h = harness()
    const cell = priorLookupPoint(IOWA.latitude, IOWA.longitude).cell
    h.cache.set(`${cell}:soilgrids`, {
      payload: { priors: [] },
      retrievedAt: '2025-01-01T00:00:00Z',
    })
    await runPriorJob(h.deps, IOWA, false)
    expect(
      h.requests.some((url) => new URL(url).host === 'rest.isric.org'),
    ).toBe(true)
  })

  it('completes an urban site with no SoilGrids prior instead of dead-lettering', async () => {
    const h = harness({ soil: urbanSoilGrids })
    const outcome = await runPriorJob(h.deps, IOWA, false)
    expect(outcome.status).toBe('completed')
    expect(outcome.emptySources).toEqual(['soilgrids'])
    const cell = priorLookupPoint(IOWA.latitude, IOWA.longitude).cell
    expect(h.cache.get(`${cell}:soilgrids`)?.payload).toEqual({ priors: [] })
  })

  it('defers without fetching when the SoilGrids bucket is empty', async () => {
    const h = harness({ tokens: { soilgrids: 0 } })
    const outcome = await runPriorJob(h.deps, IOWA, false)
    expect(outcome).toMatchObject({ retryAfterSeconds: 12, status: 'deferred' })
    expect(h.requests).toEqual([])
    expect(h.finished).toEqual([])
    expect(PRIOR_OUTCOME_HTTP_STATUS[outcome.status]).toBe(202)
  })

  it('spends no tokens on requests that cannot be claimed (no bucket starvation)', async () => {
    const h = harness({ claimable: false })
    for (let call = 0; call < 61; call += 1) {
      const outcome = await runPriorJob(h.deps, IOWA, true)
      expect(outcome.status).toBe('not_claimable')
    }
    expect(h.requests).toEqual([])
    expect(Object.fromEntries(h.tokens)).toEqual({
      open_meteo: 60,
      soilgrids: 1,
      ssurgo: 30,
    })
  })

  it('skips SSURGO and its token outside CONUS', async () => {
    const h = harness({ tokens: { ssurgo: 0 } })
    const outcome = await runPriorJob(h.deps, KENYA, false)
    expect(outcome.status).toBe('completed')
    expect(h.begins[0].costs.ssurgo).toBeUndefined()
    expect(h.requests.some((url) => url.includes('SDMDataAccess'))).toBe(false)
  })

  it('dead-letters on a failed source but keeps and caches the rest', async () => {
    const h = harness({ failing: ['rest.isric.org'] })
    const outcome = await runPriorJob(h.deps, IOWA, false)
    expect(outcome.status).toBe('dead_letter')
    expect(outcome.failedSources).toEqual(['soilgrids'])
    const cell = priorLookupPoint(IOWA.latitude, IOWA.longitude).cell
    expect(h.cache.has(`${cell}:soilgrids`)).toBe(false)
    expect(h.cache.has(`${cell}:ssurgo`)).toBe(true)
    // One upstream call per token: the job retry is the retry.
    expect(
      h.requests.filter((url) => new URL(url).host === 'rest.isric.org'),
    ).toHaveLength(1)
  })

  it('a failed cache write never turns a good answer into a failure', async () => {
    const h = harness()
    h.deps.writeCache = async () => {
      throw new Error('cache unavailable')
    }
    const outcome = await runPriorJob(h.deps, IOWA, false)
    expect(outcome.status).toBe('completed')
    expect(outcome.priors).toBe(28)
  })

  it('treats a capture time no service covers as no data, without a call or a token', async () => {
    const h = harness()
    const outcome = await runPriorJob(
      h.deps,
      { ...IOWA, capturedAt: '2027-01-01T00:00:00Z' },
      false,
    )
    expect(outcome.status).toBe('completed')
    expect(outcome.emptySources).toContain('precipitation')
    expect(h.begins[0].costs.open_meteo).toBe(1) // elevation only
    expect(h.requests.some((url) => url.includes('precipitation'))).toBe(false)
  })

  it('treats a definitive 400 from the weather service as no data, not a retry', async () => {
    const h = harness({ failing: [['hourly=precipitation', 400]] })
    const outcome = await runPriorJob(h.deps, IOWA, false)
    expect(outcome.status).toBe('completed')
    expect(outcome.emptySources).toContain('precipitation')
  })

  it('records an internal failure as a retryable dead letter', async () => {
    const h = harness()
    h.deps.writePriors = async () => {
      throw new Error('database unavailable')
    }
    const outcome = await runPriorJob(h.deps, IOWA, false)
    expect(outcome.status).toBe('dead_letter')
    expect(h.finished.at(-1)).toMatchObject({
      lastError: 'internal_failure',
      status: 'dead_letter',
    })
  })

  it('uses the documented public endpoints by default', () => {
    expect(new URL(DEFAULT_PRIOR_JOB_CONFIG.soilBase).host).toBe(
      'rest.isric.org',
    )
    expect(DEFAULT_PRIOR_JOB_CONFIG.cacheTtlDays).toBe(365)
  })
})

describe('request mode', () => {
  const key = 'service-role-key-0123456789'

  it('grants service mode only for the exact service-role key', () => {
    expect(isServiceRequest(`Bearer ${key}`, key)).toBe(true)
    expect(isServiceRequest(`bearer ${key}`, key)).toBe(true)
    expect(isServiceRequest(`Bearer ${key}x`, key)).toBe(false)
    expect(isServiceRequest(`Bearer ${key.slice(0, -1)}`, key)).toBe(false)
    expect(isServiceRequest(null, key)).toBe(false)
    expect(isServiceRequest(`Bearer ${key}`, '')).toBe(false)
  })

  it('never trusts an unsigned JWT that claims the service role', () => {
    const payload = btoa(JSON.stringify({ role: 'service_role' }))
    expect(isServiceRequest(`Bearer e30.${payload}.`, key)).toBe(false)
  })
})
