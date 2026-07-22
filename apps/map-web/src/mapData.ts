import { createClient } from '@supabase/supabase-js'
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

export type ContributionCell = { count: number; h3: string; latest: string }
export type ContributionFeatureCollection = {
  features: Array<{
    geometry: { coordinates: number[][][]; type: 'Polygon' }
    properties: { count: number; h3: string; latest: string }
    type: 'Feature'
  }>
  type: 'FeatureCollection'
}

const seedCells: ContributionCell[] = [
  { count: 1, h3: '88262b2a37fffff', latest: '2026-06-01' },
  { count: 1, h3: '887a6a09ebfffff', latest: '2026-06-06' },
  { count: 1, h3: '881f188721fffff', latest: '2026-06-11' },
  { count: 1, h3: '88a8d1b82dfffff', latest: '2026-06-16' },
  { count: 1, h3: '88be5d32e3fffff', latest: '2026-06-21' },
]

export async function loadContributionCells(): Promise<ContributionCell[]> {
  const url = import.meta.env.VITE_SUPABASE_URL
  const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY
  if (!url || !key) return seedCells
  const client = createClient<Database>(url, key)
  const response = await client
    .from('public_submissions')
    .select('h3_r8,captured_at')
    .order('captured_at', { ascending: false })
  if (response.error || !response.data) return seedCells
  const cells = new Map<string, ContributionCell>()
  for (const row of response.data) {
    if (!row.h3_r8 || !row.captured_at) continue
    const existing = cells.get(row.h3_r8)
    cells.set(row.h3_r8, {
      count: (existing?.count ?? 0) + 1,
      h3: row.h3_r8,
      latest: existing?.latest ?? row.captured_at.slice(0, 10),
    })
  }
  return [...cells.values()]
}

export function contributionFeatures(
  cells: ContributionCell[],
): ContributionFeatureCollection {
  return {
    features: cells.map((cell) => {
      const ring = cellToBoundary(cell.h3, true)
      return {
        geometry: { coordinates: [[...ring, ring[0]]], type: 'Polygon' },
        properties: { count: cell.count, h3: cell.h3, latest: cell.latest },
        type: 'Feature',
      }
    }),
    type: 'FeatureCollection',
  }
}
