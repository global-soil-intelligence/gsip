import { z } from 'zod'
import {
  elevationUrl,
  isConus,
  isDefinitiveRejection,
  parseElevation,
  parsePrecipitationWindow,
  parseSoilGridsResponse,
  parseSsurgoResponse,
  precipitationSource,
  precipitationUrl,
  priorLookupPoint,
  type PriorInput,
  soilGridsUrl,
  ssurgoQuery,
} from './prior.ts'

/**
 * WP-6c prior enrichment, independent of Supabase so it can be tested directly. The Edge
 * Function `prior-attach` adapts these dependencies to the database and `fetch`.
 *
 * Invariants:
 *  - external services see only the resolution-9 cell centre (SPEC I7);
 *  - static lookups are cached per cell; a cache hit makes no upstream call;
 *  - claiming a job and paying for its upstream calls is one atomic database step
 *    (`begin_prior_attempt`): a request that cannot be claimed, or must wait for tokens, spends
 *    nothing and claims nothing (I14);
 *  - one upstream call per token: no immediate retries; the job retry is the retry;
 *  - an empty or definitive answer completes the job ("no prior", I3); only failures dead-letter.
 */

export type StaticSource = 'soilgrids' | 'ssurgo' | 'elevation'
export type UpstreamBucket = 'soilgrids' | 'ssurgo' | 'open_meteo'
export type TokenCosts = Partial<Record<UpstreamBucket, number>>

export type PriorJobSubmission = {
  capturedAt: string
  id: string
  latitude: number
  longitude: number
}

export type CachedEntry = { payload: unknown; retrievedAt: string }

export type BeginResult =
  | { attempts: number; outcome: 'claimed' }
  | { outcome: 'deferred'; retryAfterSeconds: number }
  | { outcome: 'not_claimable' }

export type PriorJobDeps = {
  begin: (
    submissionId: string,
    ownerRequest: boolean,
    costs: TokenCosts,
  ) => Promise<BeginResult>
  fetchJson: (url: string, init: RequestInit) => Promise<unknown>
  finish: (update: {
    attempts: number
    emptySources: string[]
    lastError: string | null
    status: 'completed' | 'dead_letter'
  }) => Promise<void>
  now: () => Date
  readCache: (
    cell: string,
  ) => Promise<Partial<Record<StaticSource, CachedEntry>>>
  writeCache: (
    cell: string,
    source: StaticSource,
    payload: unknown,
  ) => Promise<void>
  writeEnrichment: (enrichment: {
    elevation?: number | null
    precip_flag?: boolean
  }) => Promise<void>
  writePriors: (rows: PriorInput[]) => Promise<void>
}

export type PriorJobConfig = {
  archiveBase: string
  cacheTtlDays: number
  forecastBase: string
  soilBase: string
  ssurgoUrl: string
}

export type PriorJobOutcome = {
  attempts: number | null
  emptySources: string[]
  failedSources: string[]
  priors: number
  retryAfterSeconds: number | null
  status: 'completed' | 'dead_letter' | 'deferred' | 'not_claimable'
}

export const DEFAULT_PRIOR_JOB_CONFIG: PriorJobConfig = {
  archiveBase: 'https://archive-api.open-meteo.com',
  cacheTtlDays: 365,
  forecastBase: 'https://api.open-meteo.com',
  soilBase: 'https://rest.isric.org',
  ssurgoUrl: 'https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest',
}

/** HTTP status for each outcome of the `prior-attach` function. */
export const PRIOR_OUTCOME_HTTP_STATUS: Record<
  PriorJobOutcome['status'],
  number
> = {
  completed: 200,
  dead_letter: 502,
  deferred: 202,
  not_claimable: 409,
}

/**
 * Service mode (retries allowed) only for the exact service-role key the function runs with,
 * compared in constant time. A decoded-but-unverified JWT claim is never trusted.
 */
export function isServiceRequest(
  authorization: string | null,
  serviceKey: string,
): boolean {
  if (!authorization || !serviceKey) return false
  const token = authorization.replace(/^Bearer\s+/i, '')
  const encoder = new TextEncoder()
  const left = encoder.encode(token)
  const right = encoder.encode(serviceKey)
  let difference = left.length ^ right.length
  for (let index = 0; index < Math.max(left.length, right.length); index += 1)
    difference |= (left[index] ?? 0) ^ (right[index] ?? 0)
  return difference === 0
}

const priorInputSchema = z.object({
  depth_bottom_cm: z.number().int(),
  depth_top_cm: z.number().int(),
  property: z.enum(['soc', 'ph', 'clay', 'sand', 'silt', 'bd', 'cec', 'n']),
  source: z.enum(['soilgrids', 'ssurgo']),
  uncertainty_hi: z.number().nullable(),
  uncertainty_lo: z.number().nullable(),
  unit: z.enum(['g/kg', 'pH', 'kg/dm3', 'cmol(+)/kg']),
  value: z.number(),
})
const priorPayloadSchema = z.object({ priors: z.array(priorInputSchema) })
const elevationPayloadSchema = z.object({ elevation: z.number().nullable() })

function fresh(
  entry: CachedEntry | undefined,
  now: Date,
  ttlDays: number,
): unknown {
  if (!entry) return undefined
  const age = now.getTime() - Date.parse(entry.retrievedAt)
  if (!Number.isFinite(age) || age > ttlDays * 24 * 60 * 60_000)
    return undefined
  return entry.payload
}

function cachedPriors(payload: unknown): PriorInput[] | undefined {
  const parsed = priorPayloadSchema.safeParse(payload)
  return parsed.success ? (parsed.data.priors as PriorInput[]) : undefined
}

function cachedElevation(payload: unknown): number | null | undefined {
  const parsed = elevationPayloadSchema.safeParse(payload)
  return parsed.success ? parsed.data.elevation : undefined
}

function outcome(
  status: PriorJobOutcome['status'],
  fields: Partial<PriorJobOutcome> = {},
): PriorJobOutcome {
  return {
    attempts: null,
    emptySources: [],
    failedSources: [],
    priors: 0,
    retryAfterSeconds: null,
    status,
    ...fields,
  }
}

export async function runPriorJob(
  deps: PriorJobDeps,
  submission: PriorJobSubmission,
  ownerRequest: boolean,
  config: PriorJobConfig = DEFAULT_PRIOR_JOB_CONFIG,
): Promise<PriorJobOutcome> {
  const point = priorLookupPoint(submission.latitude, submission.longitude)
  const conus = isConus(point.latitude, point.longitude)
  const now = deps.now()
  const cache = await deps.readCache(point.cell)

  let soilgrids = cachedPriors(fresh(cache.soilgrids, now, config.cacheTtlDays))
  let ssurgo = conus
    ? cachedPriors(fresh(cache.ssurgo, now, config.cacheTtlDays))
    : []
  let elevation = cachedElevation(
    fresh(cache.elevation, now, config.cacheTtlDays),
  )
  const precipitation = precipitationSource(submission.capturedAt, now)

  const costs: TokenCosts = {}
  if (soilgrids === undefined) costs.soilgrids = 1
  if (ssurgo === undefined) costs.ssurgo = 1
  const openMeteoCalls =
    (elevation === undefined ? 1 : 0) +
    (precipitation === 'unavailable' ? 0 : 1)
  if (openMeteoCalls) costs.open_meteo = openMeteoCalls

  const begun = await deps.begin(submission.id, ownerRequest, costs)
  if (begun.outcome === 'deferred')
    return outcome('deferred', { retryAfterSeconds: begun.retryAfterSeconds })
  if (begun.outcome === 'not_claimable') return outcome('not_claimable')
  const attempts = begun.attempts

  const failedSources: string[] = []
  const emptySources: string[] = []
  // A failed cache write never fails a source: the fetched answer is still used.
  const cacheQuietly = (source: StaticSource, payload: unknown) =>
    deps.writeCache(point.cell, source, payload).catch(() => undefined)

  try {
    if (soilgrids === undefined) {
      try {
        soilgrids = parseSoilGridsResponse(
          await deps.fetchJson(soilGridsUrl(config.soilBase, point), {}),
        )
        await cacheQuietly('soilgrids', { priors: soilgrids })
      } catch {
        failedSources.push('soilgrids')
      }
    }
    if (soilgrids?.length === 0) emptySources.push('soilgrids')

    if (ssurgo === undefined) {
      try {
        ssurgo = parseSsurgoResponse(
          await deps.fetchJson(config.ssurgoUrl, {
            body: JSON.stringify({
              format: 'JSON+COLUMNNAME',
              query: ssurgoQuery(point),
            }),
            headers: { 'Content-Type': 'application/json' },
            method: 'POST',
          }),
        )
        await cacheQuietly('ssurgo', { priors: ssurgo })
      } catch {
        failedSources.push('ssurgo')
      }
    }
    if (conus && ssurgo?.length === 0) emptySources.push('ssurgo')

    if (elevation === undefined) {
      try {
        elevation = parseElevation(
          await deps.fetchJson(elevationUrl(config.forecastBase, point), {}),
        )
        await cacheQuietly('elevation', { elevation })
      } catch (error) {
        if (isDefinitiveRejection(error)) elevation = null
        else failedSources.push('elevation')
      }
    }
    if (elevation === null) emptySources.push('elevation')

    let precipFlag: boolean | null = null
    if (precipitation !== 'unavailable') {
      try {
        precipFlag = parsePrecipitationWindow(
          await deps.fetchJson(
            precipitationUrl({
              archiveBase: config.archiveBase,
              capturedAt: submission.capturedAt,
              forecastBase: config.forecastBase,
              now,
              point,
            }),
            {},
          ),
          submission.capturedAt,
        )
      } catch (error) {
        if (!isDefinitiveRejection(error)) failedSources.push('precipitation')
      }
    }
    if (precipFlag === null && !failedSources.includes('precipitation'))
      emptySources.push('precipitation')

    const rows = [...(soilgrids ?? []), ...(ssurgo ?? [])]
    if (rows.length) await deps.writePriors(rows)
    const enrichment: { elevation?: number | null; precip_flag?: boolean } = {}
    if (elevation !== undefined) enrichment.elevation = elevation
    if (typeof precipFlag === 'boolean') enrichment.precip_flag = precipFlag
    if (Object.keys(enrichment).length) await deps.writeEnrichment(enrichment)

    const status = failedSources.length ? 'dead_letter' : 'completed'
    await deps.finish({
      attempts,
      emptySources,
      lastError: failedSources.length
        ? `source_failure:${failedSources.join(',')}`
        : null,
      status,
    })
    return outcome(status, {
      attempts,
      emptySources,
      failedSources,
      priors: rows.length,
    })
  } catch {
    await deps
      .finish({
        attempts,
        emptySources,
        lastError: 'internal_failure',
        status: 'dead_letter',
      })
      .catch(() => undefined)
    return outcome('dead_letter', {
      attempts,
      emptySources,
      failedSources: [...failedSources, 'internal'],
    })
  }
}
