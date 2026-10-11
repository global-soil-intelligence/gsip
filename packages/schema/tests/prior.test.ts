import { describe, expect, it, vi } from 'vitest'
import soilGrids from './fixtures/soilgrids.json'
import urbanSoilGrids from './fixtures/soilgrids-urban.json'
import ssurgo from './fixtures/ssurgo.json'
import { cellToLatLng, getResolution } from 'h3-js'
import {
  elevationUrl,
  fetchJsonWithRetry,
  isConus,
  parseElevation,
  parsePrecipitationWindow,
  parseSoilGridsResponse,
  parseSsurgoResponse,
  precipitationUrl,
  priorLookupPoint,
  SOILGRIDS_PROPERTY_MAPPING,
  soilGridsUrl,
  ssurgoQuery,
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

  it('gives null SSURGO horizons zero weight instead of a zero value', () => {
    const priors = parseSsurgoResponse({
      Table: [
        [
          'comppct_r',
          'hzdept_r',
          'hzdepb_r',
          'ph',
          'clay',
          'sand',
          'silt',
          'bd',
          'cec',
        ],
        ['90', '0', '20', '6.5', '32', '21', '47', null, '27.3'],
        ['90', '20', '58', '6.9', '33', '25', '42', '1.25', '27.7'],
      ],
    })
    expect(
      priors.find(
        (prior) => prior.property === 'bd' && prior.depth_bottom_cm === 30,
      )?.value,
    ).toBe(1.25)
    expect(
      priors.find(
        (prior) => prior.property === 'bd' && prior.depth_bottom_cm === 5,
      ),
    ).toBeUndefined()
  })

  it('treats an all-null (urban) SoilGrids answer as no prior, not an error', () => {
    expect(parseSoilGridsResponse(urbanSoilGrids)).toEqual([])
  })

  it('keeps the properties SoilGrids does estimate in a partial answer', () => {
    const partial = structuredClone(soilGrids) as typeof soilGrids
    const soc = partial.properties.layers.find((layer) => layer.name === 'soc')
    for (const depth of soc!.depths)
      Object.assign(depth.values, { 'Q0.05': null, 'Q0.95': null, mean: null })
    const clay = partial.properties.layers.find(
      (layer) => layer.name === 'clay',
    )
    Object.assign(clay!.depths[2].values, { mean: null })
    const priors = parseSoilGridsResponse(partial)
    expect(priors.some((prior) => prior.property === 'soc')).toBe(false)
    expect(
      priors
        .filter((prior) => prior.property === 'clay')
        .map((prior) => prior.depth_bottom_cm),
    ).toEqual([5])
    expect(priors).toHaveLength(13)
  })

  it('detects the CONUS routing boundary without exposing coordinates', () => {
    expect(isConus(41.9483, -93.625)).toBe(true)
    expect(isConus(-9, -72)).toBe(false)
  })
})

describe('lookup privacy', () => {
  it('sends external services the resolution-9 cell centre, never the precise point', () => {
    const point = priorLookupPoint(44.47591234, -73.21214321)
    expect(getResolution(point.cell)).toBe(9)
    const [latitude, longitude] = cellToLatLng(point.cell)
    expect(point.latitude).toBeCloseTo(latitude, 6)
    expect(point.longitude).toBeCloseTo(longitude, 6)
    expect(point.latitude).not.toBe(44.47591234)
    for (const url of [
      soilGridsUrl('https://rest.isric.org', point),
      elevationUrl('https://api.open-meteo.com', point),
      precipitationUrl({
        archiveBase: 'https://archive-api.open-meteo.com',
        capturedAt: '2026-10-08T15:00:00Z',
        forecastBase: 'https://api.open-meteo.com',
        now: new Date('2026-10-10T00:00:00Z'),
        point,
      }),
    ]) {
      expect(url).not.toContain('44.4759123')
      expect(url).not.toContain('73.2121432')
    }
    expect(ssurgoQuery(point)).toContain(
      `POINT(${point.longitude} ${point.latitude})`,
    )
  })
})

describe('environment enrichment', () => {
  it('parses GLO-90 elevation, treating a missing value as unknown', () => {
    expect(parseElevation({ elevation: [305] })).toBe(305)
    expect(parseElevation({ elevation: [null] })).toBeNull()
  })

  it('flags rain in the 72 hours before capture, not before the request', () => {
    const hourly = {
      hourly: {
        precipitation: [0.6, 0.6, 0, 9],
        time: [
          '2026-10-05T14:00',
          '2026-10-07T10:00',
          '2026-10-08T14:00',
          '2026-10-08T16:00',
        ],
      },
    }
    // Rain after the capture moment (16:00) must not count.
    expect(parsePrecipitationWindow(hourly, '2026-10-08T15:00:00Z')).toBe(false)
    expect(parsePrecipitationWindow(hourly, '2026-10-08T17:00:00Z')).toBe(true)
    // 2026-10-05T14:00 is outside the 72-hour window ending 2026-10-08T15:00.
    expect(
      parsePrecipitationWindow(
        {
          hourly: {
            precipitation: [5, null],
            time: ['2026-10-05T14:00', '2026-10-08T10:00'],
          },
        },
        '2026-10-08T15:00:00Z',
      ),
    ).toBeNull()
  })

  it('chooses the forecast API for recent captures and the archive for old ones', () => {
    const point = priorLookupPoint(41.9483, -93.625)
    const recent = new URL(
      precipitationUrl({
        archiveBase: 'https://archive-api.open-meteo.com',
        capturedAt: '2026-10-08T15:00:00Z',
        forecastBase: 'https://api.open-meteo.com',
        now: new Date('2026-10-10T00:00:00Z'),
        point,
      }),
    )
    expect(recent.host).toBe('api.open-meteo.com')
    expect(recent.pathname).toBe('/v1/forecast')
    expect(recent.searchParams.get('start_date')).toBe('2026-10-05')
    expect(recent.searchParams.get('end_date')).toBe('2026-10-08')
    expect(recent.searchParams.get('hourly')).toBe('precipitation')
    const old = new URL(
      precipitationUrl({
        archiveBase: 'https://archive-api.open-meteo.com',
        capturedAt: '2026-03-01T12:00:00Z',
        forecastBase: 'https://api.open-meteo.com',
        now: new Date('2026-10-10T00:00:00Z'),
        point,
      }),
    )
    expect(old.host).toBe('archive-api.open-meteo.com')
    expect(old.pathname).toBe('/v1/archive')
  })

  it('builds bounded official API URLs', () => {
    const point = priorLookupPoint(41.9483, -93.625)
    const soil = new URL(soilGridsUrl('https://rest.isric.org', point))
    expect(soil.pathname).toBe('/soilgrids/v2.0/properties/query')
    expect(soil.searchParams.getAll('property')).toHaveLength(8)
    expect(soil.searchParams.getAll('depth')).toEqual([
      '0-5cm',
      '5-15cm',
      '15-30cm',
    ])
    expect(
      new URL(elevationUrl('https://api.open-meteo.com', point)).pathname,
    ).toBe('/v1/elevation')
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
