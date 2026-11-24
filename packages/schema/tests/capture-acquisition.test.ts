import { describe, expect, it } from 'vitest'
import {
  CAPTURE_ACQUISITION_VERSION,
  CAPTURE_STANDARD_VERSION,
  CaptureAcquisitionSchema,
  cardGate,
  MAX_CAPTURE_ACQUISITION_BYTES,
  parseCaptureAcquisition,
  partitionByCalibration,
} from '../src/index'
import corpus from './fixtures/capture-acquisition-conformance.json'

// WP-COLLECT-6. Every block is fictional; no device, person or place is described.
const cases = corpus.acquisition_cases
function block(name = 'complete-calibrated-fictional') {
  const found = cases.find((item) => item.name === name)
  if (!found) throw new Error(`missing fixture ${name}`)
  return JSON.parse(found.raw) as Record<string, unknown>
}

describe('capture acquisition contract', () => {
  it.each(cases)('agrees with the shared corpus: $name', (item) => {
    if (item.valid) {
      const parsed = parseCaptureAcquisition(item.raw)
      expect(parsed.schema_version).toBe(CAPTURE_ACQUISITION_VERSION)
      expect(parsed.standard_version).toBe(CAPTURE_STANDARD_VERSION)
      expect(parsed).toEqual(JSON.parse(item.raw))
    } else {
      expect(() => parseCaptureAcquisition(item.raw)).toThrow(
        /^Invalid capture acquisition$/,
      )
    }
  })

  it('rejects with a generic error that carries no value or cause', () => {
    const secret = { ...block(), lighting: 'SECRET-VALUE' }
    let caught: unknown
    try {
      parseCaptureAcquisition(JSON.stringify(secret))
    } catch (error) {
      caught = error
    }
    expect(caught).toBeInstanceOf(Error)
    expect(String(caught)).not.toContain('SECRET')
    expect((caught as Error).cause).toBeUndefined()
    const result = CaptureAcquisitionSchema.safeParse(secret)
    expect(result.success).toBe(false)
    expect(JSON.stringify(result.error?.issues)).not.toContain('SECRET')
    expect(() =>
      parseCaptureAcquisition(' '.repeat(MAX_CAPTURE_ACQUISITION_BYTES + 1)),
    ).toThrow()
  })

  it('S1: is an RGB photo and has no room for a spectrum or a soil property', () => {
    expect(
      parseCaptureAcquisition(JSON.stringify(block())).observation_kind,
    ).toBe('rgb_photo')
    for (const extra of [
      { observation_kind: 'spectrum' },
      { wavelength_nm: [450, 550, 650] },
      { reflectance: [0.3, 0.4, 0.5] },
      { soc_g_kg: 12.5 },
      { estimate: { property: 'clay', value: 200 } },
    ])
      expect(
        CaptureAcquisitionSchema.safeParse({ ...block(), ...extra }).success,
      ).toBe(false)
  })

  it('S2: requires every field, with unknown written out', () => {
    const groups = ['device', 'camera', 'reference_card', 'location'] as const
    const whole = block()
    for (const key of Object.keys(whole)) {
      const broken = { ...whole }
      delete broken[key]
      expect(CaptureAcquisitionSchema.safeParse(broken).success).toBe(false)
    }
    for (const group of groups) {
      const inner = whole[group] as Record<string, unknown>
      for (const key of Object.keys(inner)) {
        const smaller = { ...inner }
        delete smaller[key]
        expect(
          CaptureAcquisitionSchema.safeParse({ ...whole, [group]: smaller })
            .success,
        ).toBe(false)
      }
    }
    const unknown = parseCaptureAcquisition(
      JSON.stringify(block('every-unknown-explicit')),
    )
    expect(unknown.camera.iso).toBeNull()
    expect(unknown.lighting).toBe('unknown')
    expect(unknown.location).toEqual({ consent: false, h3_r9: null })
  })

  it('S3: only one detected, identified card is calibrated', () => {
    expect(
      cardGate({ detection: 'one', cardId: 'gsip-node', cardVersion: 'v1' }),
    ).toEqual({
      calibration_status: 'calibrated',
      reference_card: {
        detection: 'one',
        card_id: 'gsip-node',
        card_version: 'v1',
      },
    })
    for (const finding of [
      { detection: 'none' },
      { detection: 'not_run' },
      { detection: 'multiple' },
      { detection: 'one' },
      { detection: 'one', cardId: 'gsip-node' },
      { detection: 'none', cardId: 'gsip-node', cardVersion: 'v1' },
      { detection: 'not_run', cardId: 'gsip-a6', cardVersion: 'v1' },
      { detection: 'one', cardId: 'Not A Card Id', cardVersion: 'v1' },
    ] as const) {
      const gate = cardGate(finding)
      expect(gate.calibration_status).toBe('uncalibrated')
      expect(gate.reference_card.card_id).toBeNull()
      expect(gate.reference_card.card_version).toBeNull()
      expect(
        CaptureAcquisitionSchema.safeParse({ ...block(), ...gate }).success,
      ).toBe(true)
    }
  })

  it('S3: partitions never mix, and a record without the block is uncalibrated', () => {
    const calibrated = { id: 1, acquisition: block() }
    const noCard = { id: 2, acquisition: block('no-card-uncalibrated') }
    const legacy = { id: 3 }
    const empty = { id: 4, acquisition: null }
    const parts = partitionByCalibration([
      calibrated,
      noCard,
      legacy,
      empty,
    ] as never[])
    expect(parts.calibrated).toEqual([calibrated])
    expect(parts.uncalibrated).toEqual([noCard, legacy, empty])
    const forged = {
      acquisition: {
        ...block('no-card-uncalibrated'),
        calibration_status: 'calibrated',
      },
    }
    expect(() => partitionByCalibration([forged] as never[])).toThrow()
  })
})
