import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { SupabaseClient } from '@supabase/supabase-js'
import type { Database } from '@gsip/schema'
import {
  cellSummary,
  contributionFeatures,
  fetchContributionCells,
  PRIOR_LAYERS,
} from '../src/mapData'

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

import { App, Legend } from '../src/App'
import { legendGradient } from '@gsip/schema'

afterEach(() => {
  cleanup()
  vi.unstubAllEnvs()
})

describe('prior legends', () => {
  it('draws every PMTiles legend from the palette that colours the tiles', () => {
    vi.stubEnv('VITE_PRIOR_TILES_BASE', 'https://tiles.example/gsip/')
    for (const layer of PRIOR_LAYERS) {
      render(<Legend layer={layer} />)
      const gradient = screen.getByTestId(`legend-gradient-${layer.id}`)
      // jsdom normalizes colours, so compare against the same normalization.
      const probe = document.createElement('i')
      probe.style.background = legendGradient(layer.palette)
      expect(gradient.style.background).toBe(probe.style.background)
      expect(gradient.style.background).not.toBe('')
      cleanup()
    }
  })

  it('shows ISRIC’s own legend for the WMS fallback it does not colour', () => {
    const soc = PRIOR_LAYERS[0]
    render(<Legend layer={soc} />)
    const image = screen.getByRole('img', {
      name: /ISRIC legend for Organic carbon/i,
    })
    expect(image.getAttribute('src')).toContain('request=GetLegendGraphic')
    expect(image.getAttribute('src')).toContain('layer=soc_0-5cm_mean')
  })
})

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
      {
        contributors: 3,
        count: 3,
        h3: '88262b2a37fffff',
        latest: '2026-06-01',
        resolution: 8,
      },
    ])
    expect(collection.features[0].geometry.type).toBe('Polygon')
    expect(collection.features[0].properties).toEqual(
      expect.objectContaining({
        count: 3,
        latest: '2026-06-01',
        resolution: 8,
      }),
    )
  })

  it('draws k-anonymous cells of all three resolutions, coarse first', () => {
    const collection = contributionFeatures([
      {
        contributors: 3,
        count: 5,
        h3: '88262b2a37fffff',
        latest: '2026-06-01',
        resolution: 8,
      },
      {
        contributors: 4,
        count: 4,
        h3: '84262b3ffffffff',
        latest: '2026-05-01',
        resolution: 4,
      },
      {
        contributors: 3,
        count: 3,
        h3: '86262b287ffffff',
        latest: '2026-05-21',
        resolution: 6,
      },
    ])
    expect(
      collection.features.map((feature) => feature.properties.resolution),
    ).toEqual([4, 6, 8])
    for (const feature of collection.features)
      expect(feature.geometry.coordinates[0].length).toBeGreaterThanOrEqual(7)
  })

  it('summarizes a cell with its resolution and contributors, never a point', () => {
    expect(
      cellSummary({
        contributors: 3,
        count: 4,
        h3: '86262b287ffffff',
        latest: '2026-05-21',
        resolution: 6,
      }),
    ).toEqual([
      '4 contributions from 3 contributors',
      'Resolution 6 cell, about 36 km²',
      'Latest: 2026-05-21',
    ])
  })

  it('pages through every public H3 aggregate beyond the REST row cap', async () => {
    const rows = Array.from({ length: 1001 }, (_, index) => ({
      h3_index: `88${index.toString(16).padStart(13, '0')}`,
      latest_submission_date: '2026-07-23',
      n_contributors: 3,
      n_submissions: index + 3,
      resolution: 8,
    }))
    const ranges: Array<[number, number]> = []
    const query = {
      gt: vi.fn(),
      order: vi.fn(),
      range: vi.fn((start: number, end: number) => {
        ranges.push([start, end])
        return Promise.resolve({
          data: rows.slice(start, end + 1),
          error: null,
        })
      }),
      select: vi.fn(),
    }
    query.select.mockReturnValue(query)
    query.gt.mockReturnValue(query)
    query.order.mockReturnValue(query)
    const client = {
      from: vi.fn(() => query),
    } as unknown as SupabaseClient<Database>

    const cells = await fetchContributionCells(client)

    expect(cells).toHaveLength(1001)
    expect(ranges).toEqual([
      [0, 999],
      [1000, 1999],
    ])
    expect(cells.at(-1)).toEqual({
      contributors: 3,
      count: 1003,
      h3: rows.at(-1)?.h3_index,
      latest: '2026-07-23',
      resolution: 8,
    })
    expect(query.select).toHaveBeenCalledWith(
      'h3_index,resolution,n_submissions,n_contributors,latest_submission_date',
    )
  })
})
