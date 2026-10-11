import { cellToParent, getResolution, isValidCell } from 'h3-js'
import { existingContributor, type GsipClient } from './supabase'
import type { ShotType } from './types'

/**
 * WP-APP-1 "My Soil": the signed-in contributor's own submissions, read through row-level
 * security. It asks only for what it shows (date, status, shots) and the private resolution-8
 * cell needed to find the public area, never coordinates or accuracy, and it never shows a cell
 * that is not public.
 */

export type MySoilStatus =
  'checking' | 'failed' | 'passed' | 'review' | 'uploading'
export type ShotState = 'failed' | 'missing' | 'passed' | 'pending' | 'review'

export type PublicArea = { cell: string; resolution: 4 | 6 | 8 }

export type MySoilEntry = {
  id: string
  capturedAt: string
  status: MySoilStatus
  shots: Record<ShotType, ShotState>
  /** The published cell this observation is counted in; null until it is public. */
  publicArea: PublicArea | null
}

/** The columns read, and nothing more: no geometry, accuracy, device or metadata. */
export const MY_SOIL_COLUMNS =
  'id, contributor_id, captured_at, status, finalized_at, h3_r8, photos(shot_type, qa_status)'
export const MY_SOIL_LIMIT = 50
const PUBLISHED_RESOLUTIONS = [8, 6, 4] as const

type Row = {
  id: string
  contributor_id: string
  captured_at: string
  status: string
  finalized_at: string | null
  h3_r8: string | null
  photos: Array<{ shot_type: string; qa_status: string | null }> | null
}

function statusOf(row: Row): MySoilStatus {
  switch (row.status) {
    case 'qa_pass':
      return 'passed'
    case 'qa_fail':
      return 'failed'
    case 'flagged':
      return 'review'
    default:
      return row.finalized_at ? 'checking' : 'uploading'
  }
}

function shotsOf(row: Row): Record<ShotType, ShotState> {
  const shots: Record<ShotType, ShotState> = {
    A: 'missing',
    B: 'missing',
    C: 'missing',
  }
  for (const photo of row.photos ?? []) {
    if (
      photo.shot_type !== 'A' &&
      photo.shot_type !== 'B' &&
      photo.shot_type !== 'C'
    )
      continue
    shots[photo.shot_type] =
      photo.qa_status === 'pass'
        ? 'passed'
        : photo.qa_status === 'fail'
          ? 'failed'
          : photo.qa_status === null
            ? 'pending'
            : 'review'
  }
  return shots
}

/** The published resolutions' cells containing a resolution-8 cell, finest first. */
function ancestry(h3R8: string | null): string[] {
  if (!h3R8 || !isValidCell(h3R8) || getResolution(h3R8) !== 8) return []
  return PUBLISHED_RESOLUTIONS.map((resolution) =>
    resolution === 8 ? h3R8 : cellToParent(h3R8, resolution),
  )
}

/**
 * The contributor's latest submissions, newest first, or null when this device has no account.
 * A passed observation is counted in the finest published cell containing it (SPEC I7: the
 * export places it at resolution 8 if that cell is published, else 6, else 4).
 */
export async function mySoil(
  client: GsipClient,
): Promise<MySoilEntry[] | null> {
  const contributor = await existingContributor(client)
  if (!contributor) return null
  const { data, error } = await client
    .from('submissions')
    .select(MY_SOIL_COLUMNS)
    .eq('contributor_id', contributor)
    .order('captured_at', { ascending: false })
    .limit(MY_SOIL_LIMIT)
  if (error) throw error
  // Row-level security already returns only the contributor's rows; checked again here.
  const rows = ((data ?? []) as Row[]).filter(
    (row) => row.contributor_id === contributor,
  )

  const candidates = new Set(
    rows
      .filter((row) => row.status === 'qa_pass')
      .flatMap((row) => ancestry(row.h3_r8)),
  )
  const published = new Map<string, PublicArea['resolution']>()
  if (candidates.size) {
    const cells = await client
      .from('h3_cells')
      .select('h3_index, resolution')
      .in('h3_index', [...candidates])
    if (cells.error) throw cells.error
    for (const cell of cells.data ?? []) {
      if (
        cell.resolution === 8 ||
        cell.resolution === 6 ||
        cell.resolution === 4
      )
        published.set(cell.h3_index, cell.resolution)
    }
  }

  return rows.map((row) => {
    const status = statusOf(row)
    const area =
      status === 'passed'
        ? ancestry(row.h3_r8).find((cell) => published.has(cell))
        : undefined
    return {
      id: row.id,
      capturedAt: row.captured_at,
      status,
      shots: shotsOf(row),
      publicArea: area
        ? { cell: area, resolution: published.get(area) ?? 8 }
        : null,
    }
  })
}
