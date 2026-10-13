import { z } from 'zod'

/** Pure synthetic contract helpers; validation never supplies peer/use authority. */
export const MAX_NODE_EXCHANGE_BYTES = 2_000_000
export const MAX_NODE_EXCHANGE_DEPTH = 12
export const MAX_NODE_EXCHANGE_SEQUENCE = 9_007_199_254_740_991
const invalidMessage = 'Invalid node exchange event'
const conflictMessage = 'Node exchange conflict'
const uuid = z
  .string()
  .length(36)
  .regex(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i)
  .transform((value) => value.toLowerCase())
const digest = z.string().regex(/^[a-f0-9]{64}$/)
const sequence = z.number().int().min(0).max(MAX_NODE_EXCHANGE_SEQUENCE)
const fraction = z.number().finite().min(0).max(1)
const context = z
  .strictObject({
    depth_top_cm: z.number().finite().min(0).max(200),
    depth_bottom_cm: z.number().finite().min(0).max(200),
    condition: z.enum(['dry', 'moist', 'wet', 'unknown']),
  })
  .refine((value) => value.depth_top_cm < value.depth_bottom_cm)
const camera = z.strictObject({
  kind: z.literal('camera_rgb'),
  source_sha256: digest,
  device_id: uuid,
  extractor_version: z.literal('rgb-summary-v1'),
  mean_rgb: z.tuple([fraction, fraction, fraction]),
  std_rgb: z.tuple([fraction, fraction, fraction]),
  pixel_count: z.number().int().min(1).max(40_000_000),
  card_present: z.boolean(),
  calibration_status: z.literal('uncalibrated'),
})
const instrument = z
  .strictObject({
    kind: z.literal('instrument_reflectance'),
    source_sha256: digest,
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
        (band, index, bands) => index === 0 || band > bands[index - 1],
      ),
  )
const measurement = z.discriminatedUnion('kind', [camera, instrument])
const scientificTuple = {
  protocol_version: z.literal('gsip-capture-v1'),
  context,
  measurement,
}
const declaration = z.strictObject({
  sample_handle: uuid,
  measurement_handle: uuid,
  ...scientificTuple,
  synthetic_claim: z.boolean(),
})
const retirement = z.strictObject({
  sample_handle: uuid,
  measurement_handles: z
    .array(uuid)
    .max(100)
    .refine((values) => new Set(values).size === values.length),
})
const common = {
  schema_version: z.literal('gsip-node-exchange-v1'),
  event_id: uuid,
  source_peer_id: uuid,
  destination_peer_id: uuid,
  scope_id: uuid,
  stream_sequence: sequence,
  previous_event_sha256: digest.nullable(),
}
const eventSchema = z
  .discriminatedUnion('kind', [
    z.strictObject({
      ...common,
      kind: z.literal('declare'),
      payload: declaration,
    }),
    z.strictObject({
      ...common,
      kind: z.literal('retire'),
      payload: retirement,
    }),
  ])
  .refine(
    (event) =>
      (event.stream_sequence === 0) === (event.previous_event_sha256 === null),
  )

function freeze<Value>(value: Value): Value {
  if (value !== null && typeof value === 'object') {
    for (const child of Object.values(value)) freeze(child)
    Object.freeze(value)
  }
  return value
}

/** Decoded values cannot prove original bytes, duplicate keys or integer token spelling. */
export const NodeExchangeEventSchema = z.unknown().transform((value, ctx) => {
  try {
    const result = eventSchema.safeParse(value)
    if (result.success) return freeze(result.data)
  } catch {
    // Decoded objects can contain input-bearing throwing getters/proxies.
  }
  ctx.addIssue({ code: 'custom', message: invalidMessage })
  return z.NEVER
})
export type NodeExchangeEvent = z.infer<typeof NodeExchangeEventSchema>
export type NodeExchangeDeclaration = Extract<
  NodeExchangeEvent,
  { kind: 'declare' }
>
export type NodeExchangeStream = readonly [string, string, string]

function fail(): never {
  throw new Error(invalidMessage)
}

function validUnicode(value: string): void {
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index)
    if (code >= 0xd800 && code <= 0xdbff) {
      const next = value.charCodeAt(++index)
      if (!(next >= 0xdc00 && next <= 0xdfff)) fail()
    } else if (code >= 0xdc00 && code <= 0xdfff) fail()
  }
}

/** Bounded preflight before full parsing; depth counts object/array containers only. */
function preflight(raw: string): void {
  let position = 0
  const whitespace = () => {
    while (' \t\r\n'.includes(raw[position] ?? '\0')) position += 1
  }
  const string = (): string => {
    if (raw[position++] !== '"') fail()
    const start = position - 1
    while (position < raw.length) {
      if (raw[position] === '\\') {
        position += 2
        continue
      }
      if (raw[position++] === '"') {
        const decoded: unknown = JSON.parse(raw.slice(start, position))
        if (typeof decoded !== 'string') fail()
        validUnicode(decoded)
        return decoded
      }
    }
    return fail()
  }
  const value = (path: readonly string[], depth: number): void => {
    whitespace()
    const token = raw[position]
    if (token === '{' || token === '[') {
      if (++depth > MAX_NODE_EXCHANGE_DEPTH) fail()
      position += 1
      const object = token === '{'
      const end = object ? '}' : ']'
      const keys = new Set<string>()
      whitespace()
      if (raw[position] === end) {
        position += 1
        return
      }
      while (position < raw.length) {
        let childPath = path
        if (object) {
          whitespace()
          const key = string()
          if (keys.has(key)) fail()
          keys.add(key)
          childPath = [...path, key]
          whitespace()
          if (raw[position++] !== ':') fail()
        }
        value(childPath, depth)
        whitespace()
        if (raw[position] === end) {
          position += 1
          return
        }
        if (raw[position++] !== ',') fail()
      }
      fail()
    }
    if (token === '"') {
      string()
      return
    }
    const start = position
    while (position < raw.length && !' \t\r\n,]}'.includes(raw[position]))
      position += 1
    const literal = raw.slice(start, position)
    const field = path.join('/')
    const bound =
      field === 'stream_sequence'
        ? '9007199254740991'
        : field === 'payload/measurement/pixel_count'
          ? '40000000'
          : null
    if (bound !== null) {
      if (
        !/^(0|[1-9][0-9]*)$/.test(literal) ||
        literal.length > bound.length ||
        (literal.length === bound.length && literal > bound) ||
        (field === 'payload/measurement/pixel_count' && literal === '0')
      )
        fail()
      return
    }
    if (['true', 'false', 'null'].includes(literal)) return
    if (
      !/^-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?$/.test(literal) ||
      !Number.isFinite(Number(literal))
    )
      fail()
  }
  whitespace()
  if (raw[position] !== '{') fail()
  value([], 0)
  whitespace()
  if (position !== raw.length) fail()
}

function snapshot(data: Uint8Array): Uint8Array<ArrayBuffer> {
  if (!(data instanceof Uint8Array)) fail()
  // The intrinsic accessor ignores subclass overrides and refuses proxy wrappers.
  const byteLength: unknown = Reflect.get(
    Uint8Array.prototype,
    'byteLength',
    data,
  )
  if (typeof byteLength !== 'number' || byteLength > MAX_NODE_EXCHANGE_BYTES)
    fail()
  return new Uint8Array(data)
}

function parseSnapshot(data: Uint8Array): NodeExchangeEvent {
  if (data[0] === 0xef && data[1] === 0xbb && data[2] === 0xbf) fail()
  const raw = new globalThis.TextDecoder('utf-8', { fatal: true }).decode(data)
  preflight(raw)
  return NodeExchangeEventSchema.parse(JSON.parse(raw))
}

export function parseNodeExchangeEvent(data: Uint8Array): NodeExchangeEvent {
  try {
    return parseSnapshot(snapshot(data))
  } catch {
    throw new Error(invalidMessage)
  }
}

export interface PreparedNodeExchangeEvent {
  readonly event: NodeExchangeEvent
  readonly sha256: string
  /** A new copy on each call: callers cannot change the retained retry bytes. */
  originalBytes(): Uint8Array
}

export async function prepareNodeExchangeEvent(
  data: Uint8Array,
): Promise<PreparedNodeExchangeEvent> {
  try {
    const bytes = snapshot(data)
    const event = parseSnapshot(bytes)
    const hash = await globalThis.crypto.subtle.digest('SHA-256', bytes)
    const sha256 = Array.from(new Uint8Array(hash), (byte) =>
      byte.toString(16).padStart(2, '0'),
    ).join('')
    return Object.freeze({ event, sha256, originalBytes: () => bytes.slice() })
  } catch {
    throw new Error(invalidMessage)
  }
}

export function nodeExchangeStream(
  event: NodeExchangeEvent,
): NodeExchangeStream {
  return privateBoundary(() => {
    const parsed = NodeExchangeEventSchema.parse(event)
    return Object.freeze([
      parsed.source_peer_id,
      parsed.destination_peer_id,
      parsed.scope_id,
    ])
  })
}

const streamSchema = z.tuple([uuid, uuid, uuid])
const slotSchema = z
  .strictObject({
    stream: streamSchema,
    event_id: uuid,
    stream_sequence: sequence,
    previous_event_sha256: digest.nullable(),
    sha256: digest,
  })
  .refine(
    (slot) =>
      (slot.stream_sequence === 0) === (slot.previous_event_sha256 === null),
  )
export type NodeExchangeSlot = z.infer<typeof slotSchema>
const bindingSchema = z.strictObject({
  stream: streamSchema,
  sample_handle: uuid,
  measurement_handle: uuid,
  ...scientificTuple,
  synthetic_restricted: z.boolean(),
})
export type NodeExchangeBinding = z.infer<typeof bindingSchema>
const aliasesSchema = z.strictObject({
  stream: streamSchema,
  ...retirement.shape,
})
export type NodeExchangeRetirementAliases = z.infer<typeof aliasesSchema>
const headSchema = z.strictObject({ stream_sequence: sequence, sha256: digest })
export type NodeExchangeHead = z.infer<typeof headSchema>

function equal(a: unknown, b: unknown): boolean {
  if (a === b) return true
  if (
    a === null ||
    b === null ||
    typeof a !== 'object' ||
    typeof b !== 'object'
  )
    return false
  const left = Object.entries(a)
  const right = Object.entries(b)
  return (
    left.length === right.length &&
    left.every(
      ([key, value]) =>
        Object.hasOwn(b, key) &&
        equal(value, (b as Record<string, unknown>)[key]),
    )
  )
}

function checked<Schema extends z.ZodType>(
  schema: Schema,
  value: unknown,
): z.output<Schema> {
  const result = schema.safeParse(value)
  if (!result.success) throw new Error(conflictMessage)
  return freeze(result.data)
}

function privateBoundary<Value>(operation: () => Value): Value {
  try {
    return operation()
  } catch {
    // Never retain a validator, accessor, iterator or proxy exception as a cause.
    throw new Error(conflictMessage)
  }
}

function factArray(value: unknown): void {
  if (!Array.isArray(value)) throw new Error(conflictMessage)
}

export function nodeExchangeSlot(
  prepared: PreparedNodeExchangeEvent,
): NodeExchangeSlot {
  return privateBoundary(() => {
    const event = NodeExchangeEventSchema.parse(prepared.event)
    return checked(slotSchema, {
      stream: nodeExchangeStream(event),
      event_id: event.event_id,
      stream_sequence: event.stream_sequence,
      previous_event_sha256: event.previous_event_sha256,
      sha256: prepared.sha256,
    })
  })
}

/** These are supplied synthetic integrity facts, never an authenticated ledger. */
function checkedSlots(slots: readonly NodeExchangeSlot[]): NodeExchangeSlot[] {
  factArray(slots)
  const identities = new Map<string, NodeExchangeSlot>()
  const positions = new Map<string, NodeExchangeSlot>()
  return slots.map((value) => {
    const slot = checked(slotSchema, value)
    const key = `${slot.stream.join('/')}/${slot.stream_sequence}`
    for (const prior of [identities.get(slot.event_id), positions.get(key)])
      if (prior && !equal(prior, slot)) throw new Error(conflictMessage)
    identities.set(slot.event_id, slot)
    positions.set(key, slot)
    return slot
  })
}

export function checkNodeExchangeIdentity(
  candidate: NodeExchangeSlot,
  slots: readonly NodeExchangeSlot[],
): 'new' | 'retry' {
  return privateBoundary(() => {
    factArray(slots)
    const normalized = checked(slotSchema, candidate)
    const all = checkedSlots([...slots, normalized])
    return all
      .slice(0, -1)
      .some((slot) => slot.event_id === normalized.event_id)
      ? 'retry'
      : 'new'
  })
}

/** Field-value comparison, not a canonical JSON hash; synthetic restrictions only grow. */
export function bindNodeExchangeMeasurement(
  event: NodeExchangeDeclaration,
  bindings: readonly NodeExchangeBinding[],
): NodeExchangeBinding {
  return privateBoundary(() => {
    factArray(bindings)
    const parsed = NodeExchangeEventSchema.parse(event)
    if (parsed.kind !== 'declare') throw new Error(conflictMessage)
    const candidate = checked(bindingSchema, {
      stream: nodeExchangeStream(parsed),
      sample_handle: parsed.payload.sample_handle,
      measurement_handle: parsed.payload.measurement_handle,
      protocol_version: parsed.payload.protocol_version,
      context: parsed.payload.context,
      measurement: parsed.payload.measurement,
      synthetic_restricted: parsed.payload.synthetic_claim,
    })
    let restricted = candidate.synthetic_restricted
    for (const fact of bindings) {
      const prior = checked(bindingSchema, fact)
      if (
        !equal(prior.stream, candidate.stream) ||
        prior.measurement_handle !== candidate.measurement_handle
      )
        continue
      if (
        !equal(
          { ...prior, synthetic_restricted: false },
          { ...candidate, synthetic_restricted: false },
        )
      )
        throw new Error(conflictMessage)
      restricted ||= prior.synthetic_restricted
    }
    return freeze({ ...candidate, synthetic_restricted: restricted })
  })
}

/** Returns aliases to restrict only in an authorized synthetic simulator; does not authenticate. */
export function nodeExchangeRetirementAliases(
  event: NodeExchangeEvent,
): NodeExchangeRetirementAliases | null {
  return privateBoundary(() => {
    const parsed = NodeExchangeEventSchema.parse(event)
    return parsed.kind === 'retire'
      ? checked(aliasesSchema, {
          stream: nodeExchangeStream(parsed),
          ...parsed.payload,
        })
      : null
  })
}

export function nodeExchangeDeclarationCovered(
  event: NodeExchangeDeclaration,
  refusals: readonly NodeExchangeRetirementAliases[],
): boolean {
  return privateBoundary(() => {
    factArray(refusals)
    const parsed = NodeExchangeEventSchema.parse(event)
    if (parsed.kind !== 'declare') throw new Error(conflictMessage)
    const stream = nodeExchangeStream(parsed)
    return refusals
      .map((value) => checked(aliasesSchema, value))
      .some(
        (refusal) =>
          equal(refusal.stream, stream) &&
          (refusal.sample_handle === parsed.payload.sample_handle ||
            refusal.measurement_handles.includes(
              parsed.payload.measurement_handle,
            )),
      )
  })
}

/** Only contiguous supplied slots advance a head; gaps and retirement aliases are independent. */
export function advanceNodeExchangeHead(
  stream: NodeExchangeStream,
  head: NodeExchangeHead | null,
  slots: readonly NodeExchangeSlot[],
): { head: NodeExchangeHead | null; advanced: number; gap: boolean } {
  return privateBoundary(() => {
    const normalizedStream = checked(streamSchema, stream)
    let current = head === null ? null : checked(headSchema, head)
    const selected = checkedSlots(slots).filter((slot) =>
      equal(slot.stream, normalizedStream),
    )
    const bySequence = new Map(
      selected.map((slot) => [slot.stream_sequence, slot]),
    )
    if (
      current &&
      bySequence.has(current.stream_sequence) &&
      bySequence.get(current.stream_sequence)?.sha256 !== current.sha256
    )
      throw new Error(conflictMessage)
    let advanced = 0
    while (
      current === null ||
      current.stream_sequence < MAX_NODE_EXCHANGE_SEQUENCE
    ) {
      const next = current === null ? 0 : current.stream_sequence + 1
      const slot = bySequence.get(next)
      if (!slot) break
      if (slot.previous_event_sha256 !== (current?.sha256 ?? null))
        throw new Error(conflictMessage)
      current = freeze({ stream_sequence: next, sha256: slot.sha256 })
      advanced += 1
    }
    return freeze({
      head: current,
      advanced,
      gap: selected.some(
        (slot) => slot.stream_sequence > (current?.stream_sequence ?? -1),
      ),
    })
  })
}
