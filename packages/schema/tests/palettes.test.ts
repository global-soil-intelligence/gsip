import { describe, expect, it } from 'vitest'
import {
  legendGradient,
  legendLabels,
  paletteLayer,
  SOILGRIDS_PALETTE,
} from '../src/palettes'
import { SOILGRIDS_PROPERTY_MAPPING } from '../src/prior'

describe('prior palettes', () => {
  it('defines strictly increasing stops with valid colours for every layer', () => {
    expect(SOILGRIDS_PALETTE.layers.map((layer) => layer.id)).toEqual([
      'soc',
      'ph',
      'clay',
    ])
    for (const layer of SOILGRIDS_PALETTE.layers) {
      expect(layer.stops.length).toBeGreaterThanOrEqual(2)
      layer.stops.forEach((stop, index) => {
        expect(stop.color).toMatch(/^#[0-9a-f]{6}$/)
        if (index)
          expect(stop.value).toBeGreaterThan(layer.stops[index - 1].value)
      })
    }
  })

  it('uses the same SoilGrids scale factors as the prior parser', () => {
    expect(paletteLayer('soc').soilgrids.scale).toBe(
      SOILGRIDS_PROPERTY_MAPPING.soc.scale,
    )
    expect(paletteLayer('ph').soilgrids.scale).toBe(
      SOILGRIDS_PROPERTY_MAPPING.phh2o.scale,
    )
    expect(paletteLayer('clay').soilgrids.scale).toBe(
      SOILGRIDS_PROPERTY_MAPPING.clay.scale,
    )
  })

  it('builds legend gradients positioned by stop value', () => {
    expect(legendGradient(paletteLayer('clay'))).toBe(
      'linear-gradient(90deg, #fff7ec 0.0%, #fdd49e 20.0%, #fc8d59 40.0%, #d7301f 70.0%, #7f0000 100.0%)',
    )
    expect(legendLabels(paletteLayer('soc'))).toEqual({
      high: '≥ 120 g/kg',
      low: '0 g/kg',
    })
    expect(legendLabels(paletteLayer('ph'))).toEqual({
      high: '≥ pH 9',
      low: '≤ pH 4',
    })
  })
})
