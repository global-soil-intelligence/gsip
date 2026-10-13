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
