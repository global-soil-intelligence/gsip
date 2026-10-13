import { describe, expect, it, vi } from 'vitest'
import * as contracts from '../src/index'
import corpus from './fixtures/library-intake-conformance.json'

const {
  InstrumentDeclarationSchema,
  LibraryIntakeRequestSchema,
  LibraryIntakeReceiptSchema,
  LibraryIntakeCapabilitiesSchema,
  parseInstrumentDeclaration,
  parseLibraryIntakeRequest,
  MAX_LIBRARY_INTAKE_BYTES,
} = contracts
const uuid = '00000000-0000-0000-0000-000000000001'
const measurement = JSON.parse(corpus.instrument_cases[0].raw) as Record<
  string,
  unknown
>
const declaration = { measurement_id: uuid, measurement }
const request = {
  schema_version: 'gsip-library-intake-v1',
  intake_id: uuid,
  node_id: uuid,
  sample_id: uuid,
  submission_id: uuid,
  protocol_version: 'gsip-capture-v1',
  context: { depth_top_cm: 0, depth_bottom_cm: 5, condition: 'dry' },
  instrument_declaration: null,
}

describe('private library caller contract', () => {
  it('accepts only the separate intake envelope and optional declaration', () => {
    expect(parseLibraryIntakeRequest(JSON.stringify(request))).toEqual(request)
    const attached = { ...request, instrument_declaration: declaration }
    expect(parseLibraryIntakeRequest(JSON.stringify(attached))).toEqual(
      attached,
    )
    expect(InstrumentDeclarationSchema.parse(declaration)).toEqual(declaration)
  })

  it('uses canonical UUID text without inventing a version/variant requirement', () => {
    const upper = 'ABCDEFAB-CDEF-ABCD-EFAB-CDEFABCDEFAB'
    expect(
      parseInstrumentDeclaration(
        JSON.stringify({ ...declaration, measurement_id: upper }),
      ).measurement_id,
    ).toBe(upper.toLowerCase())
    for (const value of ['not-a-uuid', uuid + '\n', 1, null]) {
      expect(
        LibraryIntakeRequestSchema.safeParse({ ...request, intake_id: value })
          .success,
      ).toBe(false)
    }
  })

  it.each([
    'grant_id',
    'contributor_id',
    'actor_id',
    'consent_verified',
    'pairing_verified',
    'withdrawn',
    'synthetic',
    'holdout',
    'qa_status',
    'labels',
    'storage_path',
    'photo_id',
    'document_ref',
    'timestamp',
    'source_file',
  ])('rejects caller authority or private extra field %s', (field) => {
    expect(() =>
      parseLibraryIntakeRequest(
        JSON.stringify({ ...request, [field]: 'fictional-only' }),
      ),
    ).toThrow()
  })

  it('rejects ordinary local records and unsupported schema/protocol versions', () => {
    for (const changed of [
      { ...request, schema_version: 'gsip-library-v1' },
      { ...request, protocol_version: 'unknown' },
      { ...request, instrument_declaration: undefined },
      { ...declaration, labels: [] },
    ])
      expect(() => parseLibraryIntakeRequest(JSON.stringify(changed))).toThrow()
  })

  it.each([
    { depth_top_cm: 5, depth_bottom_cm: 5, condition: 'dry' },
    { depth_top_cm: -1, depth_bottom_cm: 5, condition: 'dry' },
    { depth_top_cm: 0, depth_bottom_cm: 201, condition: 'dry' },
    { depth_top_cm: '0', depth_bottom_cm: 5, condition: 'dry' },
    { depth_top_cm: false, depth_bottom_cm: 5, condition: 'dry' },
    { depth_top_cm: 0, depth_bottom_cm: Infinity, condition: 'dry' },
    {
      depth_top_cm: 0,
      depth_bottom_cm: 5,
      condition: 'unknown',
      private_note: 'fictional-only',
    },
    { depth_top_cm: 0, depth_bottom_cm: 5, condition: 'frozen' },
  ])('rejects invalid or implicit sample context %#', (context) => {
    expect(
      LibraryIntakeRequestSchema.safeParse({ ...request, context }).success,
    ).toBe(false)
  })

  it('exposes only the safe receipt and capability fields', () => {
    for (const status of ['stored_private_unverified', 'already_stored']) {
      expect(
        LibraryIntakeReceiptSchema.parse({ intake_id: uuid, status }),
      ).toEqual({ intake_id: uuid, status })
    }
    for (const available of [false, true]) {
      expect(
        LibraryIntakeCapabilitiesSchema.parse({
          version: 'gsip-library-intake-v1',
          available,
        }),
      ).toEqual({ version: 'gsip-library-intake-v1', available })
    }
    expect(
      LibraryIntakeReceiptSchema.safeParse({
        intake_id: uuid,
        status: 'verified',
      }).success,
    ).toBe(false)
    expect(
      LibraryIntakeReceiptSchema.safeParse({
        intake_id: uuid,
        status: 'already_stored',
        grant_id: uuid,
      }).success,
    ).toBe(false)
    expect(
      LibraryIntakeCapabilitiesSchema.safeParse({
        version: 'unknown',
        available: true,
      }).success,
    ).toBe(false)
    expect(
      LibraryIntakeCapabilitiesSchema.safeParse({
        version: 'gsip-library-intake-v1',
        available: 'true',
      }).success,
    ).toBe(false)
    expect(
      LibraryIntakeCapabilitiesSchema.safeParse({
        version: 'gsip-library-intake-v1',
        available: true,
        holdout: false,
      }).success,
    ).toBe(false)
  })
})

describe('shared synthetic instrument conformance corpus', () => {
  it.each(corpus.instrument_cases)(
    '$name agrees with the Python instrument validator',
    ({ valid, raw }) => {
      const wrapped = `{"measurement_id":"${uuid}","measurement":${raw}}`
      if (valid)
        expect(parseInstrumentDeclaration(wrapped).measurement.kind).toBe(
          'instrument_reflectance',
        )
      else
        expect(() => parseInstrumentDeclaration(wrapped)).toThrow(
          'Invalid instrument declaration',
        )
    },
  )

  it.each(corpus.band_count_cases)(
    '$count bands: accepts=$valid',
    ({ count, valid }) => {
      const value = {
        ...measurement,
        wavelength_nm: Array.from({ length: count }, (_, i) => 200 + i),
        reflectance: Array.from({ length: count }, () => 0.4),
        uncertainty: Array.from({ length: count }, () => 0.01),
      }
      expect(
        InstrumentDeclarationSchema.safeParse({
          measurement_id: uuid,
          measurement: value,
        }).success,
      ).toBe(valid)
    },
  )
})

describe('bounded raw JSON and generic private errors', () => {
  it('rejects duplicate decoded keys at every envelope level, including identical values', () => {
    const rawDeclaration = JSON.stringify(declaration)
    const rawRequest = JSON.stringify({
      ...request,
      instrument_declaration: declaration,
    })
    const duplicateDeclarations = [
      `{"measurement_id":"${uuid}","measurement\\u005fid":"${uuid}","measurement":${JSON.stringify(measurement)}}`,
      rawDeclaration.replace(
        '"source_sha256":',
        '"source_sha256":"fictional","source_sha256":',
      ),
    ]
    for (const raw of duplicateDeclarations)
      expect(() => parseInstrumentDeclaration(raw)).toThrow()
    for (const raw of [
      rawRequest.replace(
        '"schema_version":',
        '"schema_version":"unknown","schema_version":',
      ),
      rawRequest.replace(
        '"depth_top_cm":0',
        '"depth_top_cm":0,"depth_top_cm":0',
      ),
      rawRequest.replace(
        '"source_sha256":',
        '"source_sha256":"fictional","source_sha256":',
      ),
    ])
      expect(() => parseLibraryIntakeRequest(raw)).toThrow()
  })

  it('enforces the inclusive UTF-8 byte limit before any JSON parse', () => {
    expect(MAX_LIBRARY_INTAKE_BYTES).toBe(2_000_000)
    for (const [raw, parse] of [
      [JSON.stringify(declaration), parseInstrumentDeclaration],
      [JSON.stringify(request), parseLibraryIntakeRequest],
    ] as const) {
      const padded = raw + ' '.repeat(MAX_LIBRARY_INTAKE_BYTES - raw.length)
      expect(() => parse(padded)).not.toThrow()
      const spy = vi.spyOn(JSON, 'parse')
      expect(() => parse(padded + ' ')).toThrow()
      expect(spy).not.toHaveBeenCalled()
      spy.mockRestore()
    }
    const oversizedUtf8 = JSON.stringify({
      private_note: 'é'.repeat(1_000_000),
    })
    expect(oversizedUtf8.length).toBeLessThan(MAX_LIBRARY_INTAKE_BYTES)
    const spy = vi.spyOn(JSON, 'parse')
    expect(() => parseInstrumentDeclaration(oversizedUtf8)).toThrow()
    expect(spy).not.toHaveBeenCalled()
    spy.mockRestore()
  })

  it('never exposes invalid values or arbitrary field names through errors', () => {
    const sentinel = 'fictional-private-value-must-not-be-echoed'
    for (const parse of [
      parseInstrumentDeclaration,
      parseLibraryIntakeRequest,
    ]) {
      let failure: unknown
      try {
        parse(`{"${sentinel}": "${sentinel}"`)
      } catch (error) {
        failure = error
      }
      expect(failure).toBeInstanceOf(Error)
      expect(String(failure)).not.toContain(sentinel)
      expect(failure).not.toHaveProperty('cause')
    }
    for (const schema of [
      InstrumentDeclarationSchema,
      LibraryIntakeRequestSchema,
    ]) {
      const result = schema.safeParse({ ...request, [sentinel]: sentinel })
      expect(result.success).toBe(false)
      if (!result.success)
        expect(JSON.stringify(result.error)).not.toContain(sentinel)
    }
  })

  it('accepts equivalent key ordering, escaping and numeric spelling', () => {
    const reordered = Object.fromEntries(Object.entries(request).reverse())
    expect(parseLibraryIntakeRequest(JSON.stringify(reordered))).toEqual(
      request,
    )
    const alternate = JSON.stringify(request)
      .replace('"schema_version"', '"schema\\u005fversion"')
      .replace('"depth_top_cm":0', '"depth_top_cm":0.0')
    expect(parseLibraryIntakeRequest(alternate)).toEqual(request)
  })

  it('stops malformed, trailing and deeply nested inputs with generic errors', () => {
    for (const raw of [
      '',
      'null',
      '[]',
      'false',
      '{} {}',
      '[',
      '['.repeat(200) + '0' + ']'.repeat(200),
    ]) {
      expect(() => parseLibraryIntakeRequest(raw)).toThrow(
        'Invalid library intake request',
      )
    }
  })
})
