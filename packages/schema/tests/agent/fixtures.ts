import { cellToChildren, cellToParent, latLngToCell } from 'h3-js'
import type { CellRange } from '../../src/agent/h3'
import type { PublicReader } from '../../src/agent/reader'
import type { H3CellRow, ReleaseRow } from '../../src/agent/schemas'

export const BURLINGTON_R8 = latLngToCell(44.4759, -73.2121, 8)
export const BURLINGTON_R9 = latLngToCell(44.4759, -73.2121, 9)
export const BURLINGTON_R6 = cellToParent(BURLINGTON_R8, 6)
export const BURLINGTON_R4 = cellToParent(BURLINGTON_R8, 4)
export const SIBLINGS_R8 = cellToChildren(BURLINGTON_R6, 8)
  .filter((cell) => cell !== BURLINGTON_R8)
  .slice(0, 3)
export const ELSEWHERE_R8 = latLngToCell(-0.3031, 36.08, 8)
/** In Burlington's resolution-6 cell, but never observed. */
export const EMPTY_R8 =
  cellToChildren(BURLINGTON_R6, 8).find(
    (cell) => cell !== BURLINGTON_R8 && !SIBLINGS_R8.includes(cell),
  ) ?? ''

export function row(
  h3Index: string,
  resolution: 4 | 6 | 8,
  observations = 5,
  contributors = 3,
): H3CellRow {
  return {
    h3_index: h3Index,
    resolution,
    n_submissions: observations,
    n_contributors: contributors,
    n_gold: 0,
    latest_submission_date: '2026-09-30',
  }
}

export const RELEASE: ReleaseRow = {
  version: '2026-10-11',
  released_at: '2026-10-11T03:20:00+00:00',
  rows: 120,
  photos: 236,
  hf_revision: '0123456789abcdef0123456789abcdef01234567',
}

/** An in-memory stand-in for PostgREST that applies the same filters the real reader sends. */
export function fakeReader(
  rows: H3CellRow[],
  release: ReleaseRow | null = RELEASE,
): PublicReader & { calls: string[] } {
  const calls: string[] = []
  return {
    calls,
    async cells(indexes) {
      calls.push(`cells:${indexes.length}`)
      return rows.filter((candidate) => indexes.includes(candidate.h3_index))
    },
    async cellsInRanges(ranges: readonly CellRange[], { after, limit }) {
      calls.push(`ranges:${ranges.length}`)
      return rows
        .filter((candidate) =>
          ranges.some(
            (range) =>
              candidate.resolution === range.resolution &&
              candidate.h3_index >= range.first &&
              candidate.h3_index <= range.last,
          ),
        )
        .filter(
          (candidate) => after === undefined || candidate.h3_index > after,
        )
        .sort((left, right) => (left.h3_index < right.h3_index ? -1 : 1))
        .slice(0, limit)
    },
    async latestRelease() {
      calls.push('release')
      return release
    },
  }
}

export const PUBLISHED: H3CellRow[] = [
  row(BURLINGTON_R8, 8, 7, 4),
  ...SIBLINGS_R8.map((cell) => row(cell, 8)),
  row(BURLINGTON_R6, 6, 12, 5),
  row(BURLINGTON_R4, 4, 30, 9),
  row(ELSEWHERE_R8, 8),
]
