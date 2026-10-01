import { describe, expect, it } from 'vitest'
import { fuzzLocation } from '../src/geo'

describe('public location fuzzing', () => {
  it('returns pinned H3 resolutions and a cell centroid', () => {
    const result = fuzzLocation(41.9483, -93.625)
    expect(result.h3R8).toMatch(/^88[0-9a-f]{13}$/)
    expect(result.h3R6).toMatch(/^86[0-9a-f]{13}$/)
    expect(result.latitude).not.toBe(41.9483)
    expect(result.longitude).not.toBe(-93.625)
  })
})
