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
  values: z.object({
    'Q0.05': z.number(),
    'Q0.95': z.number(),
    mean: z.number(),
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
    const convert = (value: number) => rounded(value * mapping.scale)
    const surface = depths[0].values
    priors.push({
      depth_bottom_cm: 5,
      depth_top_cm: 0,
      property: mapping.property,
      source: 'soilgrids',
      uncertainty_hi: convert(surface['Q0.95']),
      uncertainty_lo: convert(surface['Q0.05']),
      unit: mapping.unit,
      value: convert(surface.mean),
    })

    // SoilGrids publishes standard 0-5, 5-15 and 15-30 cm layers. GSIP's
    // 0-30 cm profile is their deterministic thickness-weighted aggregate.
    const aggregate = (key: 'Q0.05' | 'Q0.95' | 'mean') =>
      depths.reduce((sum, depth) => {
        const thickness = depth.range.bottom_depth - depth.range.top_depth
        return sum + depth.values[key] * thickness
      }, 0) / 30
    priors.push({
      depth_bottom_cm: 30,
      depth_top_cm: 0,
      property: mapping.property,
      source: 'soilgrids',
      uncertainty_hi: convert(aggregate('Q0.95')),
      uncertainty_lo: convert(aggregate('Q0.05')),
      unit: mapping.unit,
      value: convert(aggregate('mean')),
    })
  }
  return priors
}

const elevationResponseSchema = z.object({
  elevation: z.array(z.number()).min(1),
})
const weatherResponseSchema = z.object({
  daily: z.object({ precipitation_sum: z.array(z.number().nullable()).min(1) }),
})

export function parseElevation(input: unknown): number {
  return elevationResponseSchema.parse(input).elevation[0]
}

export function parseRecentPrecipitation(input: unknown): boolean {
  const values = weatherResponseSchema.parse(input).daily.precipitation_sum
  const previousThreeDays = values.slice(0, 3)
  return (
    previousThreeDays.reduce<number>((sum, value) => sum + (value ?? 0), 0) >= 1
  )
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

export function soilGridsUrl(
  base: string,
  latitude: number,
  longitude: number,
): string {
  const url = new URL('/soilgrids/v2.0/properties/query', base)
  url.searchParams.set('lat', String(latitude))
  url.searchParams.set('lon', String(longitude))
  for (const property of Object.keys(SOILGRIDS_PROPERTY_MAPPING))
    url.searchParams.append('property', property)
  for (const depth of ['0-5cm', '5-15cm', '15-30cm'])
    url.searchParams.append('depth', depth)
  for (const value of ['mean', 'Q0.05', 'Q0.95'])
    url.searchParams.append('value', value)
  return url.toString()
}

export function openMeteoUrls(
  base: string,
  latitude: number,
  longitude: number,
) {
  const elevation = new URL('/v1/elevation', base)
  elevation.searchParams.set('latitude', String(latitude))
  elevation.searchParams.set('longitude', String(longitude))
  const weather = new URL('/v1/forecast', base)
  weather.searchParams.set('latitude', String(latitude))
  weather.searchParams.set('longitude', String(longitude))
  weather.searchParams.set('daily', 'precipitation_sum')
  weather.searchParams.set('past_days', '3')
  weather.searchParams.set('forecast_days', '1')
  weather.searchParams.set('timezone', 'UTC')
  return { elevation: elevation.toString(), weather: weather.toString() }
}

export function ssurgoQuery(latitude: number, longitude: number): string {
  const point = `POINT(${longitude} ${latitude})`
  return `select co.comppct_r, ch.hzdept_r, ch.hzdepb_r,
    ch.ph1to1h2o_r as ph, ch.claytotal_r as clay,
    ch.sandtotal_r as sand, ch.silttotal_r as silt,
    ch.dbthirdbar_r as bd, ch.cec7_r as cec
  from SDA_Get_Mukey_from_intersection_with_WktWgs84('${point}') m
  join component co on co.mukey = m.mukey
  join chorizon ch on ch.cokey = co.cokey
  where co.majcompflag = 'Yes' and ch.hzdept_r < 30 and ch.hzdepb_r > 0`
}
