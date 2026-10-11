import { cellToLatLng, latLngToCell } from 'h3-js'
import { z } from 'zod'

export const SOILGRIDS_PROPERTY_MAPPING = {
  bdod: { property: 'bd', scale: 0.01, unit: 'kg/dm3' },
  cec: { property: 'cec', scale: 0.1, unit: 'cmol(+)/kg' },
  clay: { property: 'clay', scale: 1, unit: 'g/kg' },
  nitrogen: { property: 'n', scale: 0.01, unit: 'g/kg' },
  phh2o: { property: 'ph', scale: 0.1, unit: 'pH' },
  sand: { property: 'sand', scale: 1, unit: 'g/kg' },
  silt: { property: 'silt', scale: 1, unit: 'g/kg' },
  soc: { property: 'soc', scale: 0.1, unit: 'g/kg' },
} as const

export type SoilGridsCode = keyof typeof SOILGRIDS_PROPERTY_MAPPING
export type CanonicalProperty =
  (typeof SOILGRIDS_PROPERTY_MAPPING)[SoilGridsCode]['property']
export type CanonicalUnit =
  (typeof SOILGRIDS_PROPERTY_MAPPING)[SoilGridsCode]['unit']

export type PriorInput = {
  depth_bottom_cm: number
  depth_top_cm: number
  property: CanonicalProperty
  source: 'soilgrids' | 'ssurgo'
  uncertainty_hi: number | null
  uncertainty_lo: number | null
  unit: CanonicalUnit
  value: number
}

const soilGridsDepthSchema = z.object({
  range: z.object({
    bottom_depth: z.number(),
    top_depth: z.number(),
    unit_depth: z.literal('cm'),
  }),
  // SoilGrids answers null where it has no estimate (it masks built-up land, water and rock).
  values: z.object({
    'Q0.05': z.number().nullable(),
    'Q0.95': z.number().nullable(),
    mean: z.number().nullable(),
  }),
})

const soilGridsResponseSchema = z.object({
  properties: z.object({
    layers: z.array(
      z.object({
        depths: z.array(soilGridsDepthSchema),
        name: z.string(),
      }),
    ),
  }),
})

const REQUIRED_DEPTHS = [
  { bottom: 5, top: 0 },
  { bottom: 15, top: 5 },
  { bottom: 30, top: 15 },
] as const

function rounded(value: number): number {
  return Number(value.toFixed(6))
}

/**
 * Canonical prior rows from a SoilGrids response. A property with no estimate yields no row: an
 * all-null response (an urban site, for example) is a definitive "no prior", not an error.
 */
export function parseSoilGridsResponse(input: unknown): PriorInput[] {
  const response = soilGridsResponseSchema.parse(input)
  const priors: PriorInput[] = []

  for (const code of Object.keys(
    SOILGRIDS_PROPERTY_MAPPING,
  ) as SoilGridsCode[]) {
    const layer = response.properties.layers.find(
      (candidate) => candidate.name === code,
    )
    if (!layer) throw new Error(`SoilGrids response is missing ${code}`)
    const depths = REQUIRED_DEPTHS.map(({ bottom, top }) => {
      const depth = layer.depths.find(
        (candidate) =>
          candidate.range.top_depth === top &&
          candidate.range.bottom_depth === bottom,
      )
      if (!depth)
        throw new Error(
          `SoilGrids ${code} response is missing ${top}-${bottom} cm`,
        )
      return depth
    })
    const mapping = SOILGRIDS_PROPERTY_MAPPING[code]
    const convert = (value: number | null) =>
      value === null ? null : rounded(value * mapping.scale)
    const surface = depths[0].values
    if (surface.mean !== null) {
      priors.push({
        depth_bottom_cm: 5,
        depth_top_cm: 0,
        property: mapping.property,
        source: 'soilgrids',
        uncertainty_hi: convert(surface['Q0.95']),
        uncertainty_lo: convert(surface['Q0.05']),
        unit: mapping.unit,
        value: rounded(surface.mean * mapping.scale),
      })
    }

    // SoilGrids publishes standard 0-5, 5-15 and 15-30 cm layers. GSIP's
    // 0-30 cm profile is their deterministic thickness-weighted aggregate.
    // Averaging layer quantiles gives a conservative (wider than exact)
    // interval; it is documented as such (SPEC section 6).
    const aggregate = (key: 'Q0.05' | 'Q0.95' | 'mean'): number | null => {
      let sum = 0
      for (const depth of depths) {
        const value = depth.values[key]
        if (value === null) return null
        sum += value * (depth.range.bottom_depth - depth.range.top_depth)
      }
      return sum / 30
    }
    const profileMean = aggregate('mean')
    if (profileMean !== null) {
      priors.push({
        depth_bottom_cm: 30,
        depth_top_cm: 0,
        property: mapping.property,
        source: 'soilgrids',
        uncertainty_hi: convert(aggregate('Q0.95')),
        uncertainty_lo: convert(aggregate('Q0.05')),
        unit: mapping.unit,
        value: rounded(profileMean * mapping.scale),
      })
    }
  }
  return priors
}

const elevationResponseSchema = z.object({
  elevation: z.array(z.number().nullable()).min(1),
})
const hourlyPrecipitationSchema = z.object({
  hourly: z.object({
    precipitation: z.array(z.number().nullable()),
    time: z.array(z.string()),
  }),
})

/** Elevation in metres, or null where the DEM has no value. */
export function parseElevation(input: unknown): number | null {
  const value = elevationResponseSchema.parse(input).elevation[0]
  return value === null || !Number.isFinite(value) ? null : value
}

export const PRECIPITATION_WINDOW_HOURS = 72
export const PRECIPITATION_FLAG_MM = 1

/**
 * Whether at least 1 mm of rain fell in the 72 hours before capture (the main moisture
 * confounder for soil colour). Null when the window has no data.
 */
export function parsePrecipitationWindow(
  input: unknown,
  capturedAt: string,
): boolean | null {
  const { hourly } = hourlyPrecipitationSchema.parse(input)
  const end = Date.parse(capturedAt)
  if (!Number.isFinite(end)) throw new Error('capturedAt is not a timestamp')
  const start = end - PRECIPITATION_WINDOW_HOURS * 60 * 60_000
  let total = 0
  let observed = 0
  hourly.time.forEach((time, index) => {
    // Open-Meteo returns UTC hours without a zone suffix when timezone=UTC.
    const hour = Date.parse(time.endsWith('Z') ? time : `${time}Z`)
    const value = hourly.precipitation[index]
    if (!Number.isFinite(hour) || hour < start || hour >= end) return
    if (value === null || value === undefined) return
    total += value
    observed += 1
  })
  return observed === 0 ? null : total >= PRECIPITATION_FLAG_MM
}

const SSURGO_COLUMNS = [
  ['ph', 'ph', 'pH', 1],
  ['clay', 'clay', 'g/kg', 10],
  ['sand', 'sand', 'g/kg', 10],
  ['silt', 'silt', 'g/kg', 10],
  ['bd', 'bd', 'kg/dm3', 1],
  ['cec', 'cec', 'cmol(+)/kg', 1],
] as const satisfies ReadonlyArray<
  readonly [string, CanonicalProperty, CanonicalUnit, number]
>

const ssurgoResponseSchema = z.object({
  Table: z.array(z.array(z.union([z.string(), z.number(), z.null()]))),
})

export function parseSsurgoResponse(input: unknown): PriorInput[] {
  const rows = ssurgoResponseSchema.parse(input).Table
  if (rows.length < 2) return []
  const headers = rows[0].map(String)
  const indexed = rows
    .slice(1)
    .map((row) =>
      Object.fromEntries(headers.map((header, index) => [header, row[index]])),
    )
  const results: PriorInput[] = []

  for (const bottom of [5, 30] as const) {
    for (const [column, property, unit, scale] of SSURGO_COLUMNS) {
      let weighted = 0
      let totalWeight = 0
      for (const row of indexed) {
        if (row[column] === null || row[column] === '') continue
        const top = Number(row.hzdept_r)
        const rowBottom = Number(row.hzdepb_r)
        const value = Number(row[column])
        const component = Number(row.comppct_r)
        const overlap = Math.max(
          0,
          Math.min(bottom, rowBottom) - Math.max(0, top),
        )
        if (
          !Number.isFinite(value) ||
          !Number.isFinite(component) ||
          overlap === 0
        )
          continue
        const weight = overlap * component
        weighted += value * scale * weight
        totalWeight += weight
      }
      if (totalWeight > 0) {
        results.push({
          depth_bottom_cm: bottom,
          depth_top_cm: 0,
          property,
          source: 'ssurgo',
          uncertainty_hi: null,
          uncertainty_lo: null,
          unit,
          value: rounded(weighted / totalWeight),
        })
      }
    }
  }
  return results
}

export function isConus(latitude: number, longitude: number): boolean {
  return (
    latitude >= 24.2 &&
    latitude <= 49.5 &&
    longitude >= -125 &&
    longitude <= -66.5
  )
}

export async function fetchJsonWithRetry(
  fetcher: typeof fetch,
  input: string,
  init: RequestInit = {},
  options: {
    attempts?: number
    baseDelayMs?: number
    sleep?: (ms: number) => Promise<void>
  } = {},
): Promise<unknown> {
  const attempts = options.attempts ?? 4
  const baseDelayMs = options.baseDelayMs ?? 250
  const sleep =
    options.sleep ??
    ((ms: number) => new Promise((resolve) => setTimeout(resolve, ms)))
  let lastError: unknown
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    let response: Response
    try {
      response = await fetcher(input, init)
    } catch (error) {
      lastError = error
      if (attempt < attempts) await sleep(baseDelayMs * 2 ** (attempt - 1))
      continue
    }
    if (response.ok) return (await response.json()) as unknown
    if (response.status < 500 && response.status !== 429)
      throw new Error(`Upstream request failed with status ${response.status}`)
    lastError = new Error(`Retryable upstream status ${response.status}`)
    if (attempt < attempts) await sleep(baseDelayMs * 2 ** (attempt - 1))
  }
  throw lastError instanceof Error
    ? lastError
    : new Error('Upstream request failed')
}

export function soilGridsUrl(base: string, point: LookupPoint): string {
  const url = new URL('/soilgrids/v2.0/properties/query', base)
  url.searchParams.set('lat', String(point.latitude))
  url.searchParams.set('lon', String(point.longitude))
  for (const property of Object.keys(SOILGRIDS_PROPERTY_MAPPING))
    url.searchParams.append('property', property)
  for (const depth of ['0-5cm', '5-15cm', '15-30cm'])
    url.searchParams.append('depth', depth)
  for (const value of ['mean', 'Q0.05', 'Q0.95'])
    url.searchParams.append('value', value)
  return url.toString()
}

export type LookupPoint = { cell: string; latitude: number; longitude: number }

/**
 * The point external processors see (SPEC I7): the centre of the resolution-9 H3 cell (about
 * 0.1 km²), never the contributor's precise point. It is also the prior cache key.
 */
export function priorLookupPoint(
  latitude: number,
  longitude: number,
): LookupPoint {
  const cell = latLngToCell(latitude, longitude, 9)
  const [centreLatitude, centreLongitude] = cellToLatLng(cell)
  return {
    cell,
    latitude: Number(centreLatitude.toFixed(6)),
    longitude: Number(centreLongitude.toFixed(6)),
  }
}

export function elevationUrl(base: string, point: LookupPoint): string {
  const url = new URL('/v1/elevation', base)
  url.searchParams.set('latitude', String(point.latitude))
  url.searchParams.set('longitude', String(point.longitude))
  return url.toString()
}

/** The Open-Meteo forecast API serves roughly the last 92 days; older captures use the archive. */
export const FORECAST_HISTORY_DAYS = 90

function isoDate(epochMs: number): string {
  return new Date(epochMs).toISOString().slice(0, 10)
}

export function precipitationUrl(options: {
  archiveBase: string
  capturedAt: string
  forecastBase: string
  now: Date
  point: LookupPoint
}): string {
  const end = Date.parse(options.capturedAt)
  if (!Number.isFinite(end)) throw new Error('capturedAt is not a timestamp')
  const start = end - PRECIPITATION_WINDOW_HOURS * 60 * 60_000
  const archived =
    options.now.getTime() - end > FORECAST_HISTORY_DAYS * 24 * 60 * 60_000
  const url = archived
    ? new URL('/v1/archive', options.archiveBase)
    : new URL('/v1/forecast', options.forecastBase)
  url.searchParams.set('latitude', String(options.point.latitude))
  url.searchParams.set('longitude', String(options.point.longitude))
  url.searchParams.set('hourly', 'precipitation')
  url.searchParams.set('start_date', isoDate(start))
  url.searchParams.set('end_date', isoDate(end))
  url.searchParams.set('timezone', 'UTC')
  return url.toString()
}

export function ssurgoQuery(lookup: LookupPoint): string {
  const point = `POINT(${lookup.longitude} ${lookup.latitude})`
  return `select co.comppct_r, ch.hzdept_r, ch.hzdepb_r,
    ch.ph1to1h2o_r as ph, ch.claytotal_r as clay,
    ch.sandtotal_r as sand, ch.silttotal_r as silt,
    ch.dbthirdbar_r as bd, ch.cec7_r as cec
  from SDA_Get_Mukey_from_intersection_with_WktWgs84('${point}') m
  join component co on co.mukey = m.mukey
  join chorizon ch on ch.cokey = co.cokey
  where co.majcompflag = 'Yes' and ch.hzdept_r < 30 and ch.hzdepb_r > 0`
}
