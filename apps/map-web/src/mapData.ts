import { createClient } from '@supabase/supabase-js'
import type { SupabaseClient } from '@supabase/supabase-js'
import { cellToBoundary } from 'h3-js'
import type { Database } from '@gsip/schema'
import type { RasterSourceSpecification } from 'maplibre-gl'

export type PriorLayerId = 'soc' | 'ph' | 'clay'
export type PriorLayer = {
  archive: string
  high: string
  id: PriorLayerId
  label: string
  layer: string
  low: string
  mapfile: string
  unit: string
}

export const PRIOR_LAYERS: PriorLayer[] = [
  {
    archive: 'soc.pmtiles',
    high: 'High · 400 g/kg',
    id: 'soc',
    label: 'Organic carbon',
    layer: 'soc_0-5cm_mean',
    low: 'Low · 0 g/kg',
    mapfile: 'soc',
    unit: 'g/kg',
  },
  {
    archive: 'ph.pmtiles',
    high: 'Alkaline · pH 10',
    id: 'ph',
    label: 'Soil pH',
    layer: 'phh2o_0-5cm_mean',
    low: 'Acidic · pH 3',
    mapfile: 'phh2o',
    unit: 'pH',
  },
  {
    archive: 'clay.pmtiles',
    high: 'High · 800 g/kg',
    id: 'clay',
    label: 'Clay content',
    layer: 'clay_0-5cm_mean',
    low: 'Low · 0 g/kg',
    mapfile: 'clay',
    unit: 'g/kg',
  },
]

export function priorSource(layer: PriorLayer): RasterSourceSpecification {
  const archiveBase = import.meta.env.VITE_PRIOR_TILES_BASE?.replace(/\/$/, '')
  if (archiveBase)
    return {
      maxzoom: 8,
      minzoom: 0,
      tileSize: 256,
      type: 'raster',
      url: `pmtiles://${archiveBase}/${layer.archive}`,
    }
  const endpoint = `https://maps.isric.org/mapserv/${layer.mapfile}`
  const query = new URLSearchParams({
    format: 'image/png',
    height: '256',
    layers: layer.layer,
    request: 'GetMap',
    service: 'WMS',
    srs: 'EPSG:3857',
    styles: '',
    transparent: 'true',
    version: '1.1.1',
    width: '256',
  })
  return {
    maxzoom: 8,
    minzoom: 0,
    tileSize: 256,
    tiles: [`${endpoint}?${query.toString()}&bbox={bbox-epsg-3857}`],
    type: 'raster',
  }
}

export type ContributionCell = {
  contributors: number
  count: number
  h3: string
  latest: string
  resolution: number
}
export type ContributionFeatureCollection = {
  features: Array<{
    geometry: { coordinates: number[][][]; type: 'Polygon' }
    properties: ContributionCell
    type: 'Feature'
  }>
  type: 'FeatureCollection'
}

/** Approximate H3 cell areas for the k-anonymous publication resolutions (SPEC I7). */
export const RESOLUTION_AREAS: Record<number, string> = {
  4: '1,770 km²',
  6: '36 km²',
  8: '0.74 km²',
}

export function cellSummary(cell: ContributionCell): string[] {
  const area = RESOLUTION_AREAS[cell.resolution] ?? 'unknown area'
  return [
    `${cell.count} contribution${cell.count === 1 ? '' : 's'} from ${cell.contributors} contributors`,
    `Resolution ${cell.resolution} cell, about ${area}`,
    `Latest: ${cell.latest}`,
  ]
}

export async function fetchContributionCells(
  client: SupabaseClient<Database>,
  pageSize = 1000,
): Promise<ContributionCell[]> {
  const cells: ContributionCell[] = []
  for (let start = 0; ; start += pageSize) {
    const response = await client
      .from('h3_cells')
      .select(
        'h3_index,resolution,n_submissions,n_contributors,latest_submission_date',
      )
      .gt('n_submissions', 0)
      .order('h3_index')
      .range(start, start + pageSize - 1)
    if (response.error) throw response.error
    if (!response.data) throw new Error('Public aggregate response was empty')
    cells.push(
      ...response.data.map((row) => ({
        contributors: row.n_contributors,
        count: row.n_submissions,
        h3: row.h3_index,
        latest: row.latest_submission_date ?? 'Unknown',
        resolution: row.resolution,
      })),
    )
    if (response.data.length < pageSize) return cells
  }
}

export async function loadContributionCells(): Promise<ContributionCell[]> {
  const url = import.meta.env.VITE_SUPABASE_URL
  const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY
  if (!url || !key)
    throw new Error('The public contribution layer is not configured')
  return fetchContributionCells(createClient<Database>(url, key))
}

/** Coarse cells first, so finer published cells draw above the coarser ones. */
export function contributionFeatures(
  cells: ContributionCell[],
): ContributionFeatureCollection {
  return {
    features: [...cells]
      .sort(
        (left, right) =>
          left.resolution - right.resolution || left.h3.localeCompare(right.h3),
      )
      .map((cell) => {
        const ring = cellToBoundary(cell.h3, true)
        return {
          geometry: { coordinates: [[...ring, ring[0]]], type: 'Polygon' },
          properties: { ...cell },
          type: 'Feature',
        }
      }),
    type: 'FeatureCollection',
  }
}
