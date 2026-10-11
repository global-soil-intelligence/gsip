import { getResolution } from 'h3-js'
import { CAPTURE_PROTOCOL } from '../protocol.ts'
import {
  childRanges,
  FINEST_PUBLISHED_RESOLUTION,
  isWithin,
  parseCell,
  publishedAncestry,
} from './h3.ts'
import type { PublicReader } from './reader.ts'
import {
  type CellList,
  type CellResult,
  DEFAULT_LIST_LIMIT,
  type H3CellRow,
  MAX_LIST_LIMIT,
  type PublishedCell,
  type ReleaseResult,
} from './schemas.ts'

/** The request itself is wrong (a bad cell, a bad limit); the interface reports it as such. */
export class AgentInputError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'AgentInputError'
  }
}

export type ApiConfig = {
  /** Hugging Face dataset repository, e.g. `global-soil-intelligence/gsip`. */
  datasetRepo?: string
}

const DATASET_REPO = /^[A-Za-z0-9][\w.-]{0,95}\/[A-Za-z0-9][\w.-]{0,95}$/

function published(row: H3CellRow): PublishedCell {
  return {
    cell: row.h3_index,
    resolution: row.resolution,
    observations: row.n_submissions,
    contributors: row.n_contributors,
    gold_labels: row.n_gold,
    latest_observation_date: row.latest_submission_date,
  }
}

export function getProtocol() {
  return CAPTURE_PROTOCOL
}

/**
 * A cell's published state. Unpublished and empty cells give the same answer, so nobody can learn
 * where unpublished observations are (SPEC I7); coarser published cells containing it are listed.
 */
export async function getCell(
  reader: PublicReader,
  input: unknown,
): Promise<CellResult> {
  const cell = parseCell(input)
  if (!cell)
    throw new AgentInputError('cell must be an H3 cell index (15 hex digits)')
  if (getResolution(cell) > FINEST_PUBLISHED_RESOLUTION) {
    throw new AgentInputError(
      `cell must be at resolution ${FINEST_PUBLISHED_RESOLUTION} or coarser: GSIP publishes nothing finer, so a finer cell only reveals more about where you are. Ask about its resolution-${FINEST_PUBLISHED_RESOLUTION} parent instead.`,
    )
  }
  const ancestry = publishedAncestry(cell)
  const rows = await reader.cells(ancestry.map((entry) => entry.cell))
  const byCell = new Map(rows.map((row) => [row.h3_index, row]))
  const own = byCell.get(cell)
  const containing = ancestry
    .filter((entry) => entry.cell !== cell)
    .map((entry) => byCell.get(entry.cell))
    .filter((row): row is H3CellRow => row !== undefined)
    .map(published)
  return {
    cell,
    resolution: getResolution(cell),
    status: own ? 'published' : 'no_published_observations',
    published: own ? published(own) : null,
    containing,
  }
}

/** Published cells inside a cell at resolution 8 or coarser, in index order, one page at a time. */
export async function listCells(
  reader: PublicReader,
  input: { within?: unknown; limit?: unknown; after?: unknown },
): Promise<CellList> {
  const within = parseCell(input.within)
  if (!within)
    throw new AgentInputError('within must be an H3 cell index (15 hex digits)')
  if (getResolution(within) > FINEST_PUBLISHED_RESOLUTION) {
    throw new AgentInputError(
      `within must be at resolution ${FINEST_PUBLISHED_RESOLUTION} or coarser: GSIP publishes cells at resolutions 8, 6 and 4`,
    )
  }
  const limit = input.limit === undefined ? DEFAULT_LIST_LIMIT : input.limit
  if (
    typeof limit !== 'number' ||
    !Number.isInteger(limit) ||
    limit < 1 ||
    limit > MAX_LIST_LIMIT
  ) {
    throw new AgentInputError(
      `limit must be a whole number from 1 to ${MAX_LIST_LIMIT}`,
    )
  }
  let after: string | undefined
  if (input.after !== undefined && input.after !== '') {
    after = parseCell(input.after) ?? undefined
    if (!after)
      throw new AgentInputError(
        'after must be the next value of a previous page',
      )
  }
  const rows = await reader.cellsInRanges(childRanges(within), {
    after,
    limit: limit + 1,
  })
  // The range filters are exact for fixed-width hex; this keeps the answer exact regardless.
  const inside = rows.filter((row) => isWithin(row.h3_index, within))
  const page = inside.slice(0, limit)
  return {
    within,
    cells: page.map(published),
    next: inside.length > limit ? (page.at(-1)?.h3_index ?? null) : null,
  }
}

export async function getRelease(
  reader: PublicReader,
  config: ApiConfig,
): Promise<ReleaseResult> {
  const row = await reader.latestRelease()
  if (!row) return { release: null }
  const repo =
    config.datasetRepo && DATASET_REPO.test(config.datasetRepo)
      ? config.datasetRepo
      : undefined
  const datasetUrl = repo ? `https://huggingface.co/datasets/${repo}` : null
  return {
    release: {
      version: row.version,
      released_at: row.released_at,
      rows: row.rows,
      photos: row.photos,
      hf_revision: row.hf_revision,
      dataset_url: datasetUrl,
      revision_url:
        datasetUrl && row.hf_revision
          ? `${datasetUrl}/tree/${row.hf_revision}`
          : null,
    },
  }
}
