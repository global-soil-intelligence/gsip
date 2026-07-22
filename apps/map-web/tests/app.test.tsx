import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { contributionFeatures, PRIOR_LAYERS } from '../src/mapData'

vi.mock('maplibre-gl', () => ({
  addProtocol: vi.fn(),
  AttributionControl: class {},
  Map: class {
    addControl() {}
    on() {}
    remove() {}
  },
  NavigationControl: class {},
}))

vi.mock('pmtiles', () => ({
  Protocol: class {
    tile = vi.fn()
  },
}))

import { App } from '../src/App'

describe('public map', () => {
  it('offers all Phase 1 layers, units, and a contribution path', () => {
    render(<App />)
    expect(screen.getByRole('link', { name: /contribute/i })).toBeDefined()
    for (const layer of PRIOR_LAYERS) {
      expect(
        screen.getByRole('button', { name: new RegExp(layer.label, 'i') }),
      ).toBeDefined()
      expect(screen.getAllByText(layer.unit).length).toBeGreaterThan(0)
    }
  })

  it('renders contribution cells as H3 polygons with no point coordinates', () => {
    const collection = contributionFeatures([
      { count: 3, h3: '88262b2a37fffff', latest: '2026-06-01' },
    ])
    expect(collection.features[0].geometry.type).toBe('Polygon')
    expect(collection.features[0].properties).toEqual(
      expect.objectContaining({ count: 3, latest: '2026-06-01' }),
    )
  })
})
