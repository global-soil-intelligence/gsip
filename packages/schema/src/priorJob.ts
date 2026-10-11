import { z } from 'zod'
import {
  elevationUrl,
  isConus,
  parseElevation,
  parsePrecipitationWindow,
  parseSoilGridsResponse,
  parseSsurgoResponse,
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
 *  - every upstream call first takes a token from a shared bucket; without one the job is
 *    deferred before it is claimed, so it consumes no attempt (I14);
 *  - an empty answer completes the job ("no prior", I3); only failures dead-letter.
 */

export type StaticSource = 'soilgrids' | 'ssurgo' | 'elevation'
export type UpstreamBucket = 'soilgrids' | 'ssurgo' | 'open_meteo'

export type PriorJobSubmission = {
  capturedAt: string
  id: string
  latitude: number
  longitude: number
}

export type CachedEntry = { payload: unknown; retrievedAt: string }

export type PriorJobDeps = {
  claim: (submissionId: string, ownerRequest: boolean) => Promise<number | null>
  fetchJson: (
    url: string,
    init: RequestInit,
    attempts: number,
  ) => Promise<unknown>
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
  takeToken: (bucket: UpstreamBucket, cost: number) => Promise<boolean>
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
  status: 'completed' | 'dead_letter' | 'deferred' | 'not_claimable'
}

export const DEFAULT_PRIOR_JOB_CONFIG: PriorJobConfig = {
  archiveBase: 'https://archive-api.open-meteo.com',
  cacheTtlDays: 365,
  forecastBase: 'https://api.open-meteo.com',
  soilBase: 'https://rest.isric.org',
  ssurgoUrl: 'https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest',
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

  // Spend the scarcest tokens first so a deferral wastes as little as possible.
  const openMeteoCalls = (elevation === undefined ? 1 : 0) + 1
  const needed: Array<[UpstreamBucket, number]> = []
  if (soilgrids === undefined) needed.push(['soilgrids', 1])
  if (ssurgo === undefined) needed.push(['ssurgo', 1])
  needed.push(['open_meteo', openMeteoCalls])
  for (const [bucket, cost] of needed) {
    if (!(await deps.takeToken(bucket, cost)))
      return {
        attempts: null,
        emptySources: [],
        failedSources: [],
        priors: 0,
        status: 'deferred',
      }
  }

  const attempts = await deps.claim(submission.id, ownerRequest)
  if (attempts === null)
    return {
      attempts: null,
      emptySources: [],
      failedSources: [],
      priors: 0,
      status: 'not_claimable',
    }

  const failedSources: string[] = []
  const emptySources: string[] = []
  try {
    if (soilgrids === undefined) {
      try {
        // ISRIC's fair-use limit applies to retries too: one call per claimed attempt.
        soilgrids = parseSoilGridsResponse(
          await deps.fetchJson(soilGridsUrl(config.soilBase, point), {}, 1),
        )
        await deps.writeCache(point.cell, 'soilgrids', { priors: soilgrids })
      } catch {
        failedSources.push('soilgrids')
      }
    }
    if (soilgrids?.length === 0) emptySources.push('soilgrids')

    if (ssurgo === undefined) {
      try {
        ssurgo = parseSsurgoResponse(
          await deps.fetchJson(
            config.ssurgoUrl,
            {
              body: JSON.stringify({
                format: 'JSON+COLUMNNAME',
                query: ssurgoQuery(point),
              }),
              headers: { 'Content-Type': 'application/json' },
              method: 'POST',
            },
            2,
          ),
        )
        await deps.writeCache(point.cell, 'ssurgo', { priors: ssurgo })
      } catch {
        failedSources.push('ssurgo')
      }
    }
    if (conus && ssurgo?.length === 0) emptySources.push('ssurgo')

    if (elevation === undefined) {
      try {
        elevation = parseElevation(
          await deps.fetchJson(elevationUrl(config.forecastBase, point), {}, 2),
        )
        await deps.writeCache(point.cell, 'elevation', { elevation })
      } catch {
        failedSources.push('elevation')
      }
    }
    if (elevation === null) emptySources.push('elevation')

    let precipFlag: boolean | null | undefined
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
          2,
        ),
        submission.capturedAt,
      )
    } catch {
      failedSources.push('precipitation')
    }
    if (precipFlag === null) emptySources.push('precipitation')

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
    return {
      attempts,
      emptySources,
      failedSources,
      priors: rows.length,
      status,
    }
  } catch {
    await deps
      .finish({
        attempts,
        emptySources,
        lastError: 'internal_failure',
        status: 'dead_letter',
      })
      .catch(() => undefined)
    return {
      attempts,
      emptySources,
      failedSources: [...failedSources, 'internal'],
      priors: 0,
      status: 'dead_letter',
    }
  }
}
