import { describe, expect, it } from 'vitest'
import soilGrids from './fixtures/soilgrids.json'
import urbanSoilGrids from './fixtures/soilgrids-urban.json'
import ssurgo from './fixtures/ssurgo.json'
import { priorLookupPoint } from '../src/prior'
import {
  type CachedEntry,
  DEFAULT_PRIOR_JOB_CONFIG,
  type PriorJobDeps,
  runPriorJob,
  type StaticSource,
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
  cache: Map<string, CachedEntry>
  claims: Array<{ id: string; owner: boolean }>
  deps: PriorJobDeps
  enrichment: Array<Record<string, unknown>>
  finished: Array<Record<string, unknown>>
  priors: unknown[][]
  requests: string[]
  tokens: Map<UpstreamBucket, number>
}

function harness(
  options: {
    claimable?: boolean
    failing?: string[]
    soil?: unknown
    tokens?: Partial<Record<UpstreamBucket, number>>
  } = {},
): Harness {
  const state: Omit<Harness, 'deps'> = {
    cache: new Map(),
    claims: [],
    enrichment: [],
    finished: [],
    priors: [],
    requests: [],
    tokens: new Map<UpstreamBucket, number>([
      ['soilgrids', options.tokens?.soilgrids ?? 5],
      ['ssurgo', options.tokens?.ssurgo ?? 30],
      ['open_meteo', options.tokens?.open_meteo ?? 60],
    ]),
  }
  const deps: PriorJobDeps = {
    claim: async (id, owner) => {
      state.claims.push({ id, owner })
      return options.claimable === false ? null : 1
    },
    fetchJson: async (url, init) => {
      state.requests.push(url)
      const host = new URL(url).host
      if (options.failing?.some((fragment) => url.includes(fragment)))
        throw new Error('upstream 503')
      if (host === 'rest.isric.org') return options.soil ?? soilGrids
      if (host === 'SDMDataAccess.sc.egov.usda.gov'.toLowerCase()) {
        expect(init.method).toBe('POST')
        return ssurgo
      }
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
    takeToken: async (bucket, cost) => {
      const left = state.tokens.get(bucket) ?? 0
      if (left < cost) return false
      state.tokens.set(bucket, left - cost)
      return true
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
    // Only the capture-specific precipitation window is fetched again.
    expect(h.requests).toHaveLength(1)
    expect(h.requests[0]).toContain('hourly=precipitation')
    expect(h.tokens.get('soilgrids')).toBe(4)
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
    expect(h.finished[0]).toMatchObject({
      emptySources: ['soilgrids'],
      status: 'completed',
    })
    // The empty answer is cached, so the cell never asks ISRIC again.
    const cell = priorLookupPoint(IOWA.latitude, IOWA.longitude).cell
    expect(h.cache.get(`${cell}:soilgrids`)?.payload).toEqual({ priors: [] })
  })

  it('defers without claiming when the SoilGrids bucket is empty', async () => {
    const h = harness({ tokens: { soilgrids: 0 } })
    const outcome = await runPriorJob(h.deps, IOWA, false)
    expect(outcome.status).toBe('deferred')
    expect(h.claims).toEqual([])
    expect(h.requests).toEqual([])
    expect(h.finished).toEqual([])
  })

  it('makes no upstream call when the job cannot be claimed', async () => {
    const h = harness({ claimable: false })
    const outcome = await runPriorJob(h.deps, IOWA, true)
    expect(outcome.status).toBe('not_claimable')
    expect(h.claims).toEqual([{ id: IOWA.id, owner: true }])
    expect(h.requests).toEqual([])
  })

  it('skips SSURGO and its token outside CONUS', async () => {
    const h = harness({ tokens: { ssurgo: 0 } })
    const outcome = await runPriorJob(h.deps, KENYA, false)
    expect(outcome.status).toBe('completed')
    expect(h.requests.some((url) => url.includes('SDMDataAccess'))).toBe(false)
  })

  it('dead-letters on a failed source but keeps and caches the rest', async () => {
    const h = harness({ failing: ['rest.isric.org'] })
    const outcome = await runPriorJob(h.deps, IOWA, false)
    expect(outcome.status).toBe('dead_letter')
    expect(outcome.failedSources).toEqual(['soilgrids'])
    expect(h.finished[0]).toMatchObject({
      lastError: 'source_failure:soilgrids',
      status: 'dead_letter',
    })
    const cell = priorLookupPoint(IOWA.latitude, IOWA.longitude).cell
    expect(h.cache.has(`${cell}:soilgrids`)).toBe(false)
    expect(h.cache.has(`${cell}:ssurgo`)).toBe(true)
    // ISRIC's fair use counts retries: one SoilGrids call per claimed attempt.
    expect(
      h.requests.filter((url) => new URL(url).host === 'rest.isric.org'),
    ).toHaveLength(1)
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
