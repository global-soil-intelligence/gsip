import { z } from 'zod'

export const MAX_LIBRARY_INTAKE_BYTES = 2_000_000

// Opaque UUIDs need not assert a particular generation algorithm or provenance.
const uuid = z
  .string()
  .length(36)
  .regex(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i)
  .transform((value) => value.toLowerCase())
const fraction = z.number().finite().min(0).max(1)
const context = z
  .strictObject({
    depth_top_cm: z.number().finite().min(0).max(200),
    depth_bottom_cm: z.number().finite().min(0).max(200),
    condition: z.enum(['dry', 'moist', 'wet', 'unknown']),
  })
  .refine((value) => value.depth_top_cm < value.depth_bottom_cm)
const measurement = z
  .strictObject({
    kind: z.literal('instrument_reflectance'),
    source_sha256: z
      .string()
      .length(64)
      .regex(/^[a-f0-9]{64}$/),
    instrument_id: uuid,
    calibration_id: uuid,
    wavelength_nm: z
      .array(z.number().finite().min(200).max(25_000))
      .min(3)
      .max(10_000),
    reflectance: z.array(fraction).min(3).max(10_000),
    uncertainty: z.array(fraction).min(3).max(10_000),
  })
  .refine(
    (value) =>
      value.wavelength_nm.length === value.reflectance.length &&
      value.reflectance.length === value.uncertainty.length &&
      value.wavelength_nm.every(
        (wavelength, index, bands) =>
          index === 0 || wavelength > bands[index - 1],
      ),
  )
const declaration = z.strictObject({ measurement_id: uuid, measurement })
const request = z.strictObject({
  schema_version: z.literal('gsip-library-intake-v1'),
  intake_id: uuid,
  node_id: uuid,
  sample_id: uuid,
  submission_id: uuid,
  protocol_version: z.literal('gsip-capture-v1'),
  context,
  instrument_declaration: declaration.nullable(),
})

// Even schema callers receive no input values, arbitrary field names or nested error details.
function privateSchema<Schema extends z.ZodType>(
  schema: Schema,
  message: string,
) {
  return z.unknown().transform((value, ctx): z.output<Schema> => {
    const result = schema.safeParse(value)
    if (!result.success) {
      ctx.addIssue({ code: 'custom', message })
      return z.NEVER
    }
    return result.data
  })
}

export const InstrumentDeclarationSchema = privateSchema(
  declaration,
  'Invalid instrument declaration',
)
export const LibraryIntakeRequestSchema = privateSchema(
  request,
  'Invalid library intake request',
)
export const LibraryIntakeReceiptSchema = privateSchema(
  z.strictObject({
    intake_id: uuid,
    status: z.enum(['stored_private_unverified', 'already_stored']),
  }),
  'Invalid library intake receipt',
)
export const LibraryIntakeCapabilitiesSchema = privateSchema(
  z.strictObject({
    version: z.literal('gsip-library-intake-v1'),
    available: z.boolean(),
  }),
  'Invalid library intake capabilities',
)

export type InstrumentDeclaration = z.infer<typeof InstrumentDeclarationSchema>
export type LibraryIntakeRequest = z.infer<typeof LibraryIntakeRequestSchema>
export type LibraryIntakeReceipt = z.infer<typeof LibraryIntakeReceiptSchema>
export type LibraryIntakeCapabilities = z.infer<
  typeof LibraryIntakeCapabilitiesSchema
>

/** Check raw object keys before JSON.parse discards duplicates, including escaped aliases. */
function rejectDuplicateKeys(raw: string): void {
  let position = 0
  const invalid = (): never => {
    throw new Error('Invalid private JSON')
  }
  const whitespace = () => {
    while (
      raw[position] === ' ' ||
      raw[position] === '\t' ||
      raw[position] === '\r' ||
      raw[position] === '\n'
    )
      position += 1
  }
  const string = (): string => {
    if (raw[position] !== '"') return invalid()
    const start = position++
    while (position < raw.length) {
      if (raw[position] === '\\') {
        position += 2
        continue
      }
      if (raw[position++] === '"') {
        const decoded: unknown = JSON.parse(raw.slice(start, position))
        return typeof decoded === 'string' ? decoded : invalid()
      }
    }
    return invalid()
  }
  const value = (depth: number): void => {
    // Valid contract records are shallow; bound hostile nesting independently of JS stack size.
    if (depth > 64) invalid()
    whitespace()
    if (raw[position] === '{') {
      position += 1
      const keys = new Set<string>()
      whitespace()
      if (raw[position] === '}') {
        position += 1
        return
      }
      while (position < raw.length) {
        whitespace()
        const key = string()
        if (keys.has(key)) invalid()
        keys.add(key)
        whitespace()
        if (raw[position++] !== ':') invalid()
        value(depth + 1)
        whitespace()
        if (raw[position] === '}') {
          position += 1
          return
        }
        if (raw[position++] !== ',') invalid()
      }
      return invalid()
    }
    if (raw[position] === '[') {
      position += 1
      whitespace()
      if (raw[position] === ']') {
        position += 1
        return
      }
      while (position < raw.length) {
        value(depth + 1)
        whitespace()
        if (raw[position] === ']') {
          position += 1
          return
        }
        if (raw[position++] !== ',') invalid()
      }
      return invalid()
    }
    if (raw[position] === '"') {
      string()
      return
    }
    const start = position
    while (position < raw.length && !/[\s,\]}]/.test(raw[position]))
      position += 1
    if (position === start) invalid()
  }
  value(0)
  whitespace()
  if (position !== raw.length) invalid()
}

function parsePrivateJson<Schema extends z.ZodType>(
  raw: string,
  schema: Schema,
  message: string,
): z.output<Schema> {
  try {
    if (
      typeof raw !== 'string' ||
      raw.length > MAX_LIBRARY_INTAKE_BYTES ||
      new globalThis.TextEncoder().encode(raw).byteLength >
        MAX_LIBRARY_INTAKE_BYTES
    )
      throw new Error(message)
    rejectDuplicateKeys(raw)
    const parsed: unknown = JSON.parse(raw)
    return schema.parse(parsed)
  } catch {
    // JSON syntax and validator exceptions can carry private values: never attach their cause.
    throw new Error(message)
  }
}

export function parseInstrumentDeclaration(raw: string): InstrumentDeclaration {
  return parsePrivateJson(
    raw,
    InstrumentDeclarationSchema,
    'Invalid instrument declaration',
  )
}

export function parseLibraryIntakeRequest(raw: string): LibraryIntakeRequest {
  return parsePrivateJson(
    raw,
    LibraryIntakeRequestSchema,
    'Invalid library intake request',
  )
}
