import { cellToParent, getResolution, isValidCell } from 'h3-js'

/** Resolutions at which GSIP publishes k-anonymous cells (SPEC I7). */
export const PUBLISHED_RESOLUTIONS = [8, 6, 4] as const
export type PublishedResolution = (typeof PUBLISHED_RESOLUTIONS)[number]

/**
 * The finest resolution GSIP publishes, and so the finest it accepts in a question: a finer cell
 * could tell GSIP nothing more, only reveal more about where the person asking is.
 */
export const FINEST_PUBLISHED_RESOLUTION = 8

const CANONICAL_CELL = /^[0-9a-f]{15}$/

/** A canonical (lowercase, 15-digit) H3 cell index, or null if the input is not one. */
export function parseCell(input: unknown): string | null {
  if (typeof input !== 'string') return null
  const cell = input.trim().toLowerCase()
  return CANONICAL_CELL.test(cell) && isValidCell(cell) ? cell : null
}

/** The published resolutions at or coarser than this cell's, finest first, with its parents. */
export function publishedAncestry(
  cell: string,
): Array<{ cell: string; resolution: PublishedResolution }> {
  const resolution = getResolution(cell)
  return PUBLISHED_RESOLUTIONS.filter(
    (candidate) => candidate <= resolution,
  ).map((candidate) => ({
    cell: candidate === resolution ? cell : cellToParent(cell, candidate),
    resolution: candidate,
  }))
}

const RESOLUTION_SHIFT = 52n
const RESOLUTION_MASK = 0xfn << RESOLUTION_SHIFT
const DIGIT_BITS = 3n
const MAX_RESOLUTION = 15

function digitShift(position: number): bigint {
  // Digit 1 occupies bits 42-44 and digit 15 bits 0-2.
  return BigInt(MAX_RESOLUTION - position) * DIGIT_BITS
}

function hex(index: bigint): string {
  return index.toString(16).padStart(15, '0')
}

export type CellRange = {
  resolution: PublishedResolution
  first: string
  last: string
}

/**
 * Every published cell inside `parent` lies, for each published resolution at or finer than the
 * parent's, in one contiguous range of indexes: the parent's mode, base cell and digits, the
 * child resolution, any digits below the parent's, and the unused digits all 7. Fixed-width hex
 * sorts like the integers, so the database can answer "cells within" with range filters, and
 * callers still confirm each row's ancestry (`isWithin`).
 */
export function childRanges(parent: string): CellRange[] {
  const parentResolution = getResolution(parent)
  const base = BigInt(`0x${parent}`)
  return PUBLISHED_RESOLUTIONS.filter(
    (resolution) => resolution >= parentResolution,
  )
    .slice()
    .sort((left, right) => left - right)
    .map((resolution) => {
      let first =
        (base & ~RESOLUTION_MASK) | (BigInt(resolution) << RESOLUTION_SHIFT)
      let last = first
      for (
        let position = parentResolution + 1;
        position <= resolution;
        position++
      ) {
        const shift = digitShift(position)
        first &= ~(7n << shift)
        last = (last & ~(7n << shift)) | (6n << shift)
      }
      return { resolution, first: hex(first), last: hex(last) }
    })
}

export function isWithin(cell: string, parent: string): boolean {
  const parentResolution = getResolution(parent)
  const resolution = getResolution(cell)
  return (
    resolution >= parentResolution &&
    (resolution === parentResolution
      ? cell === parent
      : cellToParent(cell, parentResolution) === parent)
  )
}
