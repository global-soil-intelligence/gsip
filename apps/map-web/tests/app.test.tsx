import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { SupabaseClient } from '@supabase/supabase-js'
import type { Database } from '@gsip/schema'
import {
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

  it('pages through every public H3 aggregate beyond the REST row cap', async () => {
    const rows = Array.from({ length: 1001 }, (_, index) => ({
      h3_index: `88${index.toString(16).padStart(13, '0')}`,
      latest_submission_date: '2026-07-23',
      n_submissions: index + 1,
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
      count: 1001,
      h3: rows.at(-1)?.h3_index,
      latest: '2026-07-23',
    })
  })
})
