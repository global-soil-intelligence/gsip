import { describe, expect, it, vi } from 'vitest'
import soilGrids from './fixtures/soilgrids.json'
import ssurgo from './fixtures/ssurgo.json'
import {
  fetchJsonWithRetry,
  isConus,
  openMeteoUrls,
  parseElevation,
  parseRecentPrecipitation,
  parseSoilGridsResponse,
  parseSsurgoResponse,
  SOILGRIDS_PROPERTY_MAPPING,
  soilGridsUrl,
} from '../src/prior'

describe('prior source mapping', () => {
  it('maps every SoilGrids code to canonical names, units, depths, and uncertainty', () => {
    const priors = parseSoilGridsResponse(soilGrids)
    expect(priors).toHaveLength(16)
    expect(new Set(priors.map((prior) => prior.property))).toEqual(
      new Set(['soc', 'ph', 'clay', 'sand', 'silt', 'bd', 'cec', 'n']),
    )
    expect(
      priors.find(
        (prior) => prior.property === 'soc' && prior.depth_bottom_cm === 5,
      ),
    ).toEqual(
      expect.objectContaining({
        unit: 'g/kg',
        uncertainty_lo: 7.4,
        value: 20.2,
      }),
    )
    expect(
      priors.find(
        (prior) => prior.property === 'bd' && prior.depth_bottom_cm === 30,
      ),
    ).toEqual(
      expect.objectContaining({
        unit: 'kg/dm3',
        uncertainty_hi: 1.94,
        value: 1.545,
      }),
    )
    expect(Object.keys(SOILGRIDS_PROPERTY_MAPPING)).toHaveLength(8)
  })

  it('converts SSURGO major-component horizons into canonical profile values', () => {
    const priors = parseSsurgoResponse(ssurgo)
    expect(priors).toHaveLength(12)
    expect(
      priors.find(
        (prior) => prior.property === 'clay' && prior.depth_bottom_cm === 5,
      )?.value,
    ).toBe(320)
    expect(
      priors.find(
        (prior) => prior.property === 'ph' && prior.depth_bottom_cm === 30,
      )?.value,
    ).toBeCloseTo(6.633333)
    expect(priors.every((prior) => prior.uncertainty_lo === null)).toBe(true)
  })

  it('detects the CONUS routing boundary without exposing coordinates', () => {
    expect(isConus(41.9483, -93.625)).toBe(true)
    expect(isConus(-9, -72)).toBe(false)
  })
})

describe('environment enrichment', () => {
  it('parses GLO-90 elevation and a three-day precipitation flag', () => {
    expect(parseElevation({ elevation: [305] })).toBe(305)
    expect(
      parseRecentPrecipitation({
        daily: { precipitation_sum: [0.2, 0.4, 0.5, 0] },
      }),
    ).toBe(true)
    expect(
      parseRecentPrecipitation({
        daily: { precipitation_sum: [0, null, 0, 2] },
      }),
    ).toBe(false)
  })

  it('builds bounded official API URLs', () => {
    const soil = new URL(
      soilGridsUrl('https://rest.isric.org', 41.9483, -93.625),
    )
    expect(soil.pathname).toBe('/soilgrids/v2.0/properties/query')
    expect(soil.searchParams.getAll('property')).toHaveLength(8)
    expect(soil.searchParams.getAll('depth')).toEqual([
      '0-5cm',
      '5-15cm',
      '15-30cm',
    ])
    const meteo = openMeteoUrls('https://api.open-meteo.com', 41.9483, -93.625)
    expect(new URL(meteo.elevation).pathname).toBe('/v1/elevation')
    expect(new URL(meteo.weather).searchParams.get('past_days')).toBe('3')
  })
})

describe('bounded retry', () => {
  it('backs off and returns the first successful JSON response', async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(new Response(null, { status: 503 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true }), { status: 200 }),
      )
    const sleep = vi.fn(async () => undefined)

    await expect(
      fetchJsonWithRetry(
        fetcher,
        'https://example.invalid',
        {},
        { attempts: 4, sleep },
      ),
    ).resolves.toEqual({ ok: true })
    expect(fetcher).toHaveBeenCalledTimes(2)
    expect(sleep).toHaveBeenCalledWith(250)
  })

  it('fails closed after the configured attempt budget', async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(null, { status: 503 }))
    await expect(
      fetchJsonWithRetry(
        fetcher,
        'https://example.invalid',
        {},
        { attempts: 3, sleep: async () => undefined },
      ),
    ).rejects.toThrow('Retryable upstream status 503')
    expect(fetcher).toHaveBeenCalledTimes(3)
  })

  it('does not retry a permanent upstream rejection', async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(null, { status: 400 }))
    await expect(
      fetchJsonWithRetry(fetcher, 'https://example.invalid'),
    ).rejects.toThrow('Upstream request failed with status 400')
    expect(fetcher).toHaveBeenCalledTimes(1)
  })
})
