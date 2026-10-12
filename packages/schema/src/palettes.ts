import palette from './palettes/soilgrids.json'

/**
 * One versioned palette colours the prior tiles (pipeline/build_prior_tiles.py reads the same
 * JSON) and draws the map legends, so a legend can never disagree with its tiles (WP-6c).
 * Stops are in canonical GSIP units; `soilgrids.scale` converts raw SoilGrids values to them.
 */

export type PaletteStop = { color: string; value: number }
export type PaletteLayer = {
  id: 'clay' | 'ph' | 'soc'
  label: string
  soilgrids: { scale: number; vrt: string }
  stops: PaletteStop[]
  unit: string
}

export const SOILGRIDS_PALETTE = palette as {
  layers: PaletteLayer[]
  source: string
  version: string
}

export function paletteLayer(id: PaletteLayer['id']): PaletteLayer {
  const layer = SOILGRIDS_PALETTE.layers.find(
    (candidate) => candidate.id === id,
  )
  if (!layer) throw new Error(`No palette for ${id}`)
  return layer
}

/** CSS gradient whose colour positions follow the stop values, not equal spacing. */
export function legendGradient(layer: PaletteLayer): string {
  const first = layer.stops[0].value
  const span = layer.stops[layer.stops.length - 1].value - first
  const positions = layer.stops.map(
    (stop) =>
      `${stop.color} ${(((stop.value - first) / span) * 100).toFixed(1)}%`,
  )
  return `linear-gradient(90deg, ${positions.join(', ')})`
}

export function legendLabels(layer: PaletteLayer): {
  high: string
  low: string
} {
  const format = (value: number) =>
    layer.unit === 'pH' ? `pH ${value}` : `${value} ${layer.unit}`
  const low = layer.stops[0].value
  const high = layer.stops[layer.stops.length - 1].value
  return {
    high: `≥ ${format(high)}`,
    low: low === 0 ? format(low) : `≤ ${format(low)}`,
  }
}
