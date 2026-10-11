import {
  cellToCenterChild,
  cellToChildren,
  getRes0Cells,
  getResolution,
  latLngToCell,
} from 'h3-js'
import { describe, expect, it } from 'vitest'
import {
  childRanges,
  isWithin,
  parseCell,
  publishedAncestry,
} from '../../src/agent/h3'
import {
  BURLINGTON_R4,
  BURLINGTON_R6,
  BURLINGTON_R8,
  BURLINGTON_R9,
} from './fixtures'

describe('cell input', () => {
  it('accepts canonical H3 cells in any case and refuses everything else', () => {
    expect(parseCell(BURLINGTON_R8.toUpperCase())).toBe(BURLINGTON_R8)
    expect(parseCell(` ${BURLINGTON_R8} `)).toBe(BURLINGTON_R8)
    for (const bad of [
      '',
      'not-a-cell',
      '8f2b8cb563fffff0',
      '0000000000000000',
      'ffffffffffffff',
      `${BURLINGTON_R8.slice(0, 14)}g`,
      '8a2b8cb563fffff;drop table',
      42,
      null,
    ]) {
      expect(parseCell(bad)).toBeNull()
    }
  })

  it('lists the published resolutions a cell belongs to, finest first', () => {
    expect(publishedAncestry(BURLINGTON_R9)).toEqual([
      { cell: BURLINGTON_R8, resolution: 8 },
      { cell: BURLINGTON_R6, resolution: 6 },
      { cell: BURLINGTON_R4, resolution: 4 },
    ])
    expect(publishedAncestry(BURLINGTON_R6)).toEqual([
      { cell: BURLINGTON_R6, resolution: 6 },
      { cell: BURLINGTON_R4, resolution: 4 },
    ])
    expect(publishedAncestry(getRes0Cells()[0] ?? '')).toEqual([])
  })
})

describe('cells within an area', () => {
  // Ordinary hexagons and the pentagon at the start of the base cells, across parent resolutions.
  const parents = [
    BURLINGTON_R4,
    BURLINGTON_R6,
    BURLINGTON_R8,
    latLngToCell(-33.8688, 151.2093, 3),
    latLngToCell(51.5072, -0.1276, 5),
    cellToChildren(getRes0Cells()[4] ?? '', 2)[0] ?? '',
  ]

  it.each(parents)(
    'bounds every published-resolution child of %s',
    (parent) => {
      const ranges = childRanges(parent)
      expect(ranges.map((range) => range.resolution)).toEqual(
        [4, 6, 8].filter((resolution) => resolution >= getResolution(parent)),
      )
      for (const range of ranges) {
        expect(range.first).toBe(cellToCenterChild(parent, range.resolution))
        if (range.resolution - getResolution(parent) > 4) continue // too many to enumerate
        const children = cellToChildren(parent, range.resolution).sort()
        // Exactly the children: the first and last indexes of the range are themselves children.
        expect(children[0]).toBe(range.first)
        expect(children.at(-1)).toBe(range.last)
      }
    },
  )

  it('confirms ancestry exactly', () => {
    expect(isWithin(BURLINGTON_R8, BURLINGTON_R4)).toBe(true)
    expect(isWithin(BURLINGTON_R8, BURLINGTON_R8)).toBe(true)
    expect(isWithin(BURLINGTON_R4, BURLINGTON_R8)).toBe(false)
    expect(isWithin(latLngToCell(-0.3031, 36.08, 8), BURLINGTON_R4)).toBe(false)
  })
})
