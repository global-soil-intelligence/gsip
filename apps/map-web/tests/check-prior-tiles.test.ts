import { SOILGRIDS_PALETTE } from '@gsip/schema'
import { describe, expect, it } from 'vitest'
import { checkPriorTiles } from '../scripts/check-prior-tiles.mjs'

const version = SOILGRIDS_PALETTE.version

function archives(stamps: Record<string, unknown>) {
  const opened: string[] = []
  return {
    open: (url: string) => {
      opened.push(url)
      return {
        getMetadata: async () => {
          if (!(url in stamps)) throw new Error('Bad response code: 404')
          return stamps[url]
        },
      }
    },
    opened,
  }
}

function stampsFor(
  base: string,
  paletteVersion = version,
): Record<string, unknown> {
  return Object.fromEntries(
    SOILGRIDS_PALETTE.layers.map((layer) => [
      `${base}/${version}/${layer.id}.pmtiles`,
      { gsip_layer: layer.id, gsip_palette_version: paletteVersion },
    ]),
  )
}

describe('prior tiles deploy gate', () => {
  it('passes when every archive carries the palette version the legends use', async () => {
    const reader = archives(stampsFor('https://tiles.example/gsip'))
    const problems = await checkPriorTiles({
      base: 'https://tiles.example/gsip/',
      open: reader.open,
      palette: SOILGRIDS_PALETTE,
    })
    expect(problems).toEqual([])
    expect(reader.opened).toEqual(
      SOILGRIDS_PALETTE.layers.map(
        (layer) => `https://tiles.example/gsip/${version}/${layer.id}.pmtiles`,
      ),
    )
  })

  it('fails when the archives were coloured with another palette', async () => {
    const reader = archives(stampsFor('https://tiles.example', '2020-01-01'))
    const problems = await checkPriorTiles({
      base: 'https://tiles.example',
      open: reader.open,
      palette: SOILGRIDS_PALETTE,
    })
    expect(problems).toHaveLength(SOILGRIDS_PALETTE.layers.length)
    expect(problems[0]).toMatch(/palette 2020-01-01, but the legends use/)
  })

  it('fails when an archive is missing, unstamped or holds another layer', async () => {
    const stamps = stampsFor('https://tiles.example')
    const [first, second, third] = Object.keys(stamps)
    delete stamps[first]
    stamps[second] = {}
    stamps[third] = { gsip_layer: 'soc', gsip_palette_version: version }
    const problems = await checkPriorTiles({
      base: 'https://tiles.example',
      open: archives(stamps).open,
      palette: SOILGRIDS_PALETTE,
    })
    expect(problems).toEqual([
      expect.stringMatching(/unreadable \(Bad response code: 404\)/),
      expect.stringMatching(/palette unknown/),
      expect.stringMatching(/holds layer soc/),
    ])
  })
})
