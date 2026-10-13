import { describe, expect, it, vi } from 'vitest'
import * as contracts from '../src/index'
import corpus from './fixtures/node-exchange-conformance.json'

it('supplies the LIB-5A byte parser without changing existing contracts', () => {
  expect(contracts).toHaveProperty('parseNodeExchangeEvent')
})

const {
  parseNodeExchangeEvent: parse,
  prepareNodeExchangeEvent: prepare,
  nodeExchangeStream: stream,
  nodeExchangeSlot: slot,
  checkNodeExchangeIdentity: identity,
  bindNodeExchangeMeasurement: bind,
  advanceNodeExchangeHead: advance,
  nodeExchangeRetirementAliases: aliases,
  nodeExchangeDeclarationCovered: covered,
  NodeExchangeEventSchema,
  MAX_NODE_EXCHANGE_BYTES,
} = contracts
const bytes = (raw: string) => new globalThis.TextEncoder().encode(raw)
const raw = corpus.event_cases[0].raw
const decoded = () => JSON.parse(raw)
const uuid = (n: number) =>
  `00000000-0000-0000-0000-${n.toString(16).padStart(12, '0')}`
const declare = (changes = {}) => {
  const value = parse(bytes(JSON.stringify({ ...decoded(), ...changes })))
  if (value.kind !== 'declare')
    throw new Error('Expected synthetic declaration')
  return value
}

describe('decoded boundary errors cannot expose hostile getters or proxies', () => {
  const sentinel = 'PROBE_PRIVATE_VALUE_73541'
  const rejectAccess = (): never => {
    throw new Error(sentinel)
  }
  const proxy = <Value extends object>(value: Value): Value =>
    new Proxy(value, {
      get: rejectAccess,
      ownKeys: rejectAccess,
      getOwnPropertyDescriptor: rejectAccess,
    })
  const generic = (operation: () => unknown) => {
    let failure: unknown
    try {
      operation()
    } catch (error) {
      failure = error
    }
    expect(failure).toBeInstanceOf(Error)
    expect((failure as Error).message).toMatch(
      /^(Invalid node exchange event|Node exchange conflict)$/,
    )
    expect(String(failure)).not.toContain(sentinel)
    expect(failure).not.toHaveProperty('cause')
  }
  it('safeParse and parse report only a generic custom issue for getter/proxy access', async () => {
    const getter = Object.defineProperty(decoded(), 'kind', {
      get: rejectAccess,
    })
    for (const value of [
      getter,
      proxy(decoded()),
      { ...decoded(), payload: proxy(decoded().payload) },
    ]) {
      const result = NodeExchangeEventSchema.safeParse(value)
      expect(result.success).toBe(false)
      if (!result.success) {
        expect(result.error.issues).toEqual([
          { code: 'custom', message: 'Invalid node exchange event', path: [] },
        ])
        expect(JSON.stringify(result.error)).not.toContain(sentinel)
      }
      const asyncResult = await NodeExchangeEventSchema.safeParseAsync(value)
      expect(asyncResult.success).toBe(false)
      expect(() => NodeExchangeEventSchema.parse(value)).toThrow(
        'Invalid node exchange event',
      )
    }
  })
  it('guards every semantic helper and prepared/slot/binding/refusal/head access', async () => {
    const valid = declare()
    const prepared = await prepare(bytes(raw))
    const stored = slot(prepared)
    const binding = bind(valid, [])
    const retire = parse(
      bytes(
        JSON.stringify({
          ...decoded(),
          kind: 'retire',
          payload: { sample_handle: uuid(5), measurement_handles: [] },
        }),
      ),
    )
    const refusal = aliases(retire)!
    const badEvent = proxy(valid)
    const operations = [
      () => stream(badEvent),
      () => bind(badEvent, []),
      () => aliases(badEvent),
      () => covered(badEvent, []),
      () => slot(proxy(prepared)),
      () =>
        slot(
          Object.defineProperty({ ...prepared }, 'sha256', {
            get: rejectAccess,
          }),
        ),
      () => identity(proxy(stored), []),
      () => identity(stored, [proxy(stored)]),
      () => identity(stored, proxy([stored])),
      () => bind(valid, [proxy(binding)]),
      () => bind(valid, proxy([binding])),
      () => covered(valid, [proxy(refusal)]),
      () => covered(valid, proxy([refusal])),
      () => advance(proxy(stream(valid)), null, []),
      () =>
        advance(
          stream(valid),
          proxy({ stream_sequence: 0, sha256: prepared.sha256 }),
          [],
        ),
      () => advance(stream(valid), null, proxy([stored])),
      () => advance(stream(valid), null, [proxy(stored)]),
    ]
    for (const operation of operations) generic(operation)
  })
  it('refuses malformed/nonarray supplied fact collections generically', async () => {
    const valid = declare()
    const stored = slot(await prepare(bytes(raw)))
    for (const value of [null, {}, new Set(), '', proxy({})]) {
      generic(() =>
        identity(stored, value as unknown as contracts.NodeExchangeSlot[]),
      )
      generic(() =>
        bind(valid, value as unknown as contracts.NodeExchangeBinding[]),
      )
      generic(() =>
        covered(
          valid,
          value as unknown as contracts.NodeExchangeRetirementAliases[],
        ),
      )
      generic(() =>
        advance(
          stream(valid),
          null,
          value as unknown as contracts.NodeExchangeSlot[],
        ),
      )
    }
  })
})

describe('shared synthetic byte contract', () => {
  it.each(corpus.event_cases)('$name accepts=$valid', ({ raw, valid }) => {
    if (valid)
      expect(parse(bytes(raw)).schema_version).toBe('gsip-node-exchange-v1')
    else expect(() => parse(bytes(raw))).toThrow('Invalid node exchange event')
  })
  it.each(corpus.byte_cases)('$name is refused', ({ hex }) => {
    const data = new Uint8Array(
      hex.match(/../g)!.map((value) => Number.parseInt(value, 16)),
    )
    expect(() => parse(data)).toThrow('Invalid node exchange event')
  })
  it.each(corpus.band_count_cases)(
    '$count bands accepts=$valid',
    ({ count, valid }) => {
      const value = JSON.parse(corpus.event_cases[1].raw)
      value.payload.measurement.wavelength_nm = Array.from(
        { length: count },
        (_, index) => 200 + index,
      )
      value.payload.measurement.reflectance = Array.from(
        { length: count },
        () => 0.4,
      )
      value.payload.measurement.uncertainty = Array.from(
        { length: count },
        () => 0.01,
      )
      if (valid) expect(() => parse(bytes(JSON.stringify(value)))).not.toThrow()
      else expect(() => parse(bytes(JSON.stringify(value)))).toThrow()
    },
  )
  it('checks the inclusive byte bound before decode/parse and accepts bytes only', () => {
    expect(
      parse(
        bytes(raw + ' '.repeat(MAX_NODE_EXCHANGE_BYTES - bytes(raw).length)),
      ).kind,
    ).toBe('declare')
    const decoder = vi.spyOn(globalThis.TextDecoder.prototype, 'decode')
    const parser = vi.spyOn(JSON, 'parse')
    for (const value of [
      new Uint8Array(MAX_NODE_EXCHANGE_BYTES + 1),
      raw,
      [],
      new ArrayBuffer(1),
      null,
    ])
      expect(() => parse(value as Uint8Array)).toThrow(
        'Invalid node exchange event',
      )
    expect(decoder).not.toHaveBeenCalled()
    expect(parser).not.toHaveBeenCalled()
    vi.restoreAllMocks()
  })
  it('uses the intrinsic typed-array byte length before copying subclass buffers', () => {
    class SpoofedLength extends Uint8Array {
      get byteLength() {
        return 0
      }
    }
    const data = new SpoofedLength(MAX_NODE_EXCHANGE_BYTES + 1)
    data.fill(32)
    data.set(bytes(raw), data.length - bytes(raw).length)
    let copies = 0
    const watched = new Proxy(globalThis.Uint8Array, {
      construct(target, argumentsList, newTarget) {
        copies += 1
        return Reflect.construct(target, argumentsList, newTarget)
      },
    })
    vi.stubGlobal('Uint8Array', watched)
    const decoder = vi.spyOn(globalThis.TextDecoder.prototype, 'decode')
    try {
      expect(() => parse(data)).toThrow('Invalid node exchange event')
      expect(copies).toBe(0)
      expect(decoder).not.toHaveBeenCalled()
    } finally {
      decoder.mockRestore()
      vi.unstubAllGlobals()
    }
  })
  it('counts containers and distinguishes valid surrogate pairs from unpaired ones before full parse', () => {
    const candidates = [
      ['{"x":' + '['.repeat(11) + '0' + ']'.repeat(11) + '}', true],
      ['{"x":' + '['.repeat(12) + '0' + ']'.repeat(12) + '}', false],
      ['{"x":"\\ud83d\\ude00"}', true],
      ['{"x":"\\ud83d"}', false],
      ['{"\\ude00":0}', false],
    ] as const
    for (const [candidate, fullParse] of candidates) {
      const spy = vi.spyOn(JSON, 'parse')
      expect(() => parse(bytes(candidate))).toThrow(
        'Invalid node exchange event',
      )
      expect(spy.mock.calls.some(([value]) => value === candidate)).toBe(
        fullParse,
      )
      spy.mockRestore()
    }
  })
  it('exposes generic errors without values, arbitrary field names or causes', async () => {
    const sentinel = 'fictional-private-value-must-not-be-echoed'
    for (const data of [
      bytes(`{"${sentinel}":"${sentinel}"`),
      bytes(JSON.stringify({ ...decoded(), [sentinel]: sentinel })),
    ]) {
      for (const operation of [() => parse(data), () => prepare(data)]) {
        try {
          await operation()
          expect.fail('Expected invalid bytes')
        } catch (error) {
          expect(String(error)).not.toContain(sentinel)
          expect(error).not.toHaveProperty('cause')
        }
      }
    }
    const result = NodeExchangeEventSchema.safeParse({
      ...decoded(),
      [sentinel]: sentinel,
    })
    expect(result.success).toBe(false)
    if (!result.success)
      expect(JSON.stringify(result.error)).not.toContain(sentinel)
  })
})

describe('exact bytes and immutable supplied facts', () => {
  it('normalizes actual UUID letter case while retaining distinct original retry bytes', async () => {
    const id = 'abcdefab-cdef-abcd-efab-cdefabcdefab'
    const value = {
      ...decoded(),
      event_id: id,
      source_peer_id: id,
      destination_peer_id: id,
      scope_id: id,
    }
    const lower = await prepare(bytes(JSON.stringify(value)))
    const upper = await prepare(
      bytes(
        JSON.stringify({
          ...value,
          event_id: id.toUpperCase(),
          source_peer_id: id.toUpperCase(),
        }),
      ),
    )
    expect(upper.event).toEqual(lower.event)
    expect(() => identity(slot(upper), [slot(lower)])).toThrow(
      'Node exchange conflict',
    )
    expect(
      identity(
        {
          ...slot(lower),
          event_id: id.toUpperCase(),
          stream: [id.toUpperCase(), id.toUpperCase(), id.toUpperCase()],
        },
        [slot(lower)],
      ),
    ).toBe('retry')
    const original = declare({
      payload: {
        ...decoded().payload,
        sample_handle: id,
        measurement_handle: id,
        measurement: { ...decoded().payload.measurement, device_id: id },
      },
    })
    const binding = bind(original, [])
    const repeated = declare({
      payload: {
        ...original.payload,
        sample_handle: id.toUpperCase(),
        measurement_handle: id.toUpperCase(),
        measurement: {
          ...original.payload.measurement,
          device_id: id.toUpperCase(),
        },
      },
    })
    expect(bind(repeated, [binding])).toEqual(binding)
  })
  it('retains bytes before hash await and prevents caller/returned buffer or nested-value mutation', async () => {
    const input = bytes(raw)
    const pending = prepare(input)
    input.fill(0)
    const first = await pending
    first.originalBytes().fill(0)
    expect(first.originalBytes()).toEqual(bytes(raw))
    expect(first.sha256).toBe(corpus.camera_sha256)
    expect(identity(slot(first), [])).toBe('new')
    expect(identity(slot(first), [slot(first)])).toBe('retry')
    expect(Object.isFrozen(first.event.payload)).toBe(true)
    if (
      first.event.kind === 'declare' &&
      first.event.payload.measurement.kind === 'camera_rgb'
    ) {
      const measurement = first.event.payload.measurement
      expect(Object.isFrozen(measurement.mean_rgb)).toBe(true)
      expect(() => {
        measurement.mean_rgb[0] = 1
      }).toThrow()
    }
    for (const alternate of [
      raw + '\n',
      raw.replace('"depth_top_cm":0', '"depth_top_cm":0.0'),
      raw.replace('"event_id"', '"event\\u005fid"'),
    ]) {
      const changed = await prepare(bytes(alternate))
      expect(changed.event).toEqual(first.event)
      expect(() => identity(slot(changed), [slot(first)])).toThrow(
        'Node exchange conflict',
      )
    }
  })
  it('keeps event identity and sequence-slot ownership across normalized streams', async () => {
    const first = slot(await prepare(bytes(raw)))
    for (const change of [
      { event_id: uuid(50) },
      { scope_id: uuid(51) },
      { source_peer_id: uuid(52) },
      { destination_peer_id: uuid(53) },
      { stream_sequence: 1, previous_event_sha256: first.sha256 },
    ]) {
      const candidate = slot(
        await prepare(bytes(JSON.stringify({ ...decoded(), ...change }))),
      )
      expect(() => identity(candidate, [first])).toThrow(
        'Node exchange conflict',
      )
    }
    expect(
      identity(
        {
          ...first,
          event_id: first.event_id.toUpperCase(),
          stream: first.stream.map((id) => id.toUpperCase()) as [
            string,
            string,
            string,
          ],
        },
        [first],
      ),
    ).toBe('retry')
  })
  it('keeps scientific bindings immutable and synthetic restriction monotonic', () => {
    const original = declare()
    const binding = bind(original, [])
    const repeated = declare({
      event_id: uuid(55),
      payload: { ...original.payload, synthetic_claim: false },
    })
    expect(bind(repeated, [binding]).synthetic_restricted).toBe(true)
    const equalFields = JSON.parse(
      raw.replace('"depth_top_cm":0', '"depth_top_cm":0.0'),
    )
    equalFields.event_id = uuid(56)
    expect(bind(declare(equalFields), [binding])).toEqual(binding)
    for (const payload of [
      { ...original.payload, sample_handle: uuid(57) },
      {
        ...original.payload,
        context: { ...original.payload.context, depth_bottom_cm: 6 },
      },
      {
        ...original.payload,
        measurement: {
          ...original.payload.measurement,
          source_sha256: 'f'.repeat(64),
        },
      },
    ])
      expect(() =>
        bind(declare({ event_id: uuid(58), payload }), [binding]),
      ).toThrow('Node exchange conflict')
    const supplied = structuredClone(binding)
    const copied = bind(repeated, [supplied])
    supplied.context.depth_bottom_cm = 20
    expect(copied.context.depth_bottom_cm).toBe(5)
    expect(Object.isFrozen(copied.context)).toBe(true)
  })
})

it('advances contiguous predecessors, holds gaps and independently classifies retirement aliases', async () => {
  const first = await prepare(bytes(raw))
  const second = await prepare(
    bytes(
      JSON.stringify({
        ...decoded(),
        event_id: uuid(60),
        stream_sequence: 1,
        previous_event_sha256: first.sha256,
      }),
    ),
  )
  const third = await prepare(
    bytes(
      JSON.stringify({
        ...decoded(),
        kind: 'retire',
        event_id: uuid(61),
        stream_sequence: 2,
        previous_event_sha256: second.sha256,
        payload: { sample_handle: uuid(5), measurement_handles: [] },
      }),
    ),
  )
  const key = stream(first.event)
  expect(advance(key, null, [slot(third)])).toEqual({
    head: null,
    advanced: 0,
    gap: true,
  })
  const refusal = aliases(third.event)!
  expect(Object.keys(refusal).sort()).toEqual([
    'measurement_handles',
    'sample_handle',
    'stream',
  ])
  expect(covered(declare(), [refusal])).toBe(true)
  expect(covered(declare({ scope_id: uuid(70) }), [refusal])).toBe(false)
  const partial = advance(key, null, [slot(first), slot(third)])
  expect(partial).toEqual({
    head: { stream_sequence: 0, sha256: first.sha256 },
    advanced: 1,
    gap: true,
  })
  expect(advance(key, partial.head, [slot(third), slot(second)])).toEqual({
    head: { stream_sequence: 2, sha256: third.sha256 },
    advanced: 2,
    gap: false,
  })
  expect(() =>
    advance(key, partial.head, [
      { ...slot(second), previous_event_sha256: 'f'.repeat(64) },
    ]),
  ).toThrow('Node exchange conflict')
  expect(() =>
    advance(key, partial.head, [{ ...slot(first), sha256: 'f'.repeat(64) }]),
  ).toThrow('Node exchange conflict')
})
