import { describe, expect, it } from 'vitest'
import capture from '../../../apps/capture-pwa/src/App.tsx?raw'
import design from '../../../card/design.py?raw'
import anonymity from '../../../pipeline/k_anonymity.py?raw'
import schema from '../../../supabase/migrations/20260722164749_wp1_schema.sql?raw'
import { SOILGRIDS_PROPERTY_MAPPING } from '../src/prior'
import { CAPTURE_PROTOCOL } from '../src/protocol'

describe('the capture protocol served to people and agents', () => {
  it('names the card the generator prints', () => {
    const patches = [...design.matchAll(/Patch\("([a-z_]+)"/g)].map(
      (match) => match[1],
    )
    expect(CAPTURE_PROTOCOL.card.patches).toEqual(patches)
    expect(design).toContain(`MARKER_ID = ${CAPTURE_PROTOCOL.card.marker.id}`)
  })

  it('makes printing optional without changing required shots or the protocol shape', () => {
    expect(CAPTURE_PROTOCOL.version).toBe('1.1')
    expect(CAPTURE_PROTOCOL.card.optional).toBe(true)
    expect(CAPTURE_PROTOCOL.summary).toMatch(/No printed card is needed/)
    expect(CAPTURE_PROTOCOL.card.without_card).toMatch(/uncalibrated/)
    expect(
      CAPTURE_PROTOCOL.shots.map(({ id, required }) => ({ id, required })),
    ).toEqual([
      { id: 'A', required: true },
      { id: 'B', required: true },
      { id: 'C', required: false },
    ])
    for (const shot of CAPTURE_PROTOCOL.shots.slice(0, 2))
      expect(shot.instructions).toMatch(/optional physical reference card/)
    expect(CAPTURE_PROTOCOL.quality_checks.join(' ')).toMatch(
      /not reflectance calibration/,
    )
  })

  it('offers the descriptions the database accepts', () => {
    const landCovers = /land_cover in \(([^)]*)\)/.exec(schema)?.[1] ?? ''
    expect(
      [...landCovers.matchAll(/'([a-z]+)'/g)].map((match) => match[1]),
    ).toEqual(CAPTURE_PROTOCOL.descriptions.land_cover)
    for (const cover of CAPTURE_PROTOCOL.descriptions.land_cover) {
      expect(capture).toContain(`'${cover}'`)
    }
  })

  it('lists every canonical property with its unit', () => {
    expect(
      CAPTURE_PROTOCOL.properties.map(({ name, unit }) => [name, unit]).sort(),
    ).toEqual(
      Object.values(SOILGRIDS_PROPERTY_MAPPING)
        .map(({ property, unit }) => [property, unit])
        .sort(),
    )
  })

  it('keeps the privacy rules the export enforces', () => {
    expect(anonymity).toContain(
      `K_ANONYMITY = ${CAPTURE_PROTOCOL.privacy.minimum_contributors_per_cell}`,
    )
    expect(anonymity).toMatch(/PUBLISHED_RESOLUTIONS = \(8, 6, 4\)/)
    expect(CAPTURE_PROTOCOL.privacy.published_resolutions).toEqual([8, 6, 4])
  })

  it('describes estimates, never a soil test (I5)', () => {
    expect(JSON.stringify(CAPTURE_PROTOCOL)).not.toMatch(/soil[\s-]+test/i)
  })
})
