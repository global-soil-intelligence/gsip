import type { CellRange } from './h3.ts'
import { isPublishableKey } from './keys.ts'
import {
  type H3CellRow,
  h3CellRowSchema,
  type ReleaseRow,
  releaseRowSchema,
} from './schemas.ts'

/** The database was unreachable or answered with an error; the interface reports 503. */
export class PublicReadUnavailable extends Error {
  constructor() {
    super('GSIP public data is temporarily unavailable')
    this.name = 'PublicReadUnavailable'
  }
}

/** Everything the public interfaces read: the anonymous role's view of the database (I12). */
export type PublicReader = {
  cells: (indexes: readonly string[]) => Promise<H3CellRow[]>
  cellsInRanges: (
    ranges: readonly CellRange[],
    options: { after?: string; limit: number },
  ) => Promise<H3CellRow[]>
  latestRelease: () => Promise<ReleaseRow | null>
}

const CELL_COLUMNS =
  'h3_index,resolution,n_submissions,n_contributors,n_gold,latest_submission_date'
const RELEASE_COLUMNS = 'version,released_at,rows,photos,hf_revision'
const TIMEOUT_MS = 8000

type Fetch = (input: string, init?: RequestInit) => Promise<Response>

/**
 * Reads PostgREST with the project's publishable key only, so the anonymous role's grants and
 * row-level security bound every read. It never sees, and could not use, any other key (I12).
 */
export function postgrestReader(options: {
  url: string
  publishableKey: string
  fetch?: Fetch
}): PublicReader {
  if (!isPublishableKey(options.publishableKey)) {
    throw new Error('gsip-public reads only with a publishable key (SPEC I12)')
  }
  const base = `${options.url.replace(/\/+$/, '')}/rest/v1`
  const doFetch: Fetch = options.fetch ?? ((input, init) => fetch(input, init))
  const headers: Record<string, string> = {
    Accept: 'application/json',
    apikey: options.publishableKey,
  }
  // Legacy anon keys are JWTs and also go in Authorization; new publishable keys do not.
  if (options.publishableKey.split('.').length === 3) {
    headers.Authorization = `Bearer ${options.publishableKey}`
  }

  async function rows(
    path: string,
    query: URLSearchParams,
  ): Promise<unknown[]> {
    let response: Response
    try {
      response = await doFetch(`${base}/${path}?${query.toString()}`, {
        headers,
        signal: AbortSignal.timeout(TIMEOUT_MS),
      })
    } catch {
      throw new PublicReadUnavailable()
    }
    if (!response.ok) throw new PublicReadUnavailable()
    const body: unknown = await response.json().catch(() => null)
    if (!Array.isArray(body)) throw new PublicReadUnavailable()
    return body
  }

  function parseCells(body: unknown[]): H3CellRow[] {
    return body.map((row) => {
      const parsed = h3CellRowSchema.safeParse(row)
      if (!parsed.success) throw new PublicReadUnavailable()
      return parsed.data
    })
  }

  return {
    async cells(indexes) {
      if (!indexes.length) return []
      const query = new URLSearchParams({
        select: CELL_COLUMNS,
        h3_index: `in.(${indexes.join(',')})`,
      })
      return parseCells(await rows('h3_cells', query))
    },
    async cellsInRanges(ranges, { after, limit }) {
      if (!ranges.length) return []
      const query = new URLSearchParams({
        select: CELL_COLUMNS,
        or: `(${ranges
          .map(
            (range) =>
              `and(resolution.eq.${range.resolution},h3_index.gte.${range.first},h3_index.lte.${range.last})`,
          )
          .join(',')})`,
        order: 'h3_index.asc',
        limit: String(limit),
      })
      if (after) query.append('h3_index', `gt.${after}`)
      return parseCells(await rows('h3_cells', query))
    },
    async latestRelease() {
      const query = new URLSearchParams({
        select: RELEASE_COLUMNS,
        order: 'released_at.desc',
        limit: '1',
      })
      const [first] = await rows('dataset_releases', query)
      if (first === undefined) return null
      const parsed = releaseRowSchema.safeParse(first)
      if (!parsed.success) throw new PublicReadUnavailable()
      return parsed.data
    },
  }
}
