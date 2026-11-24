/**
 * How a phone photograph of soil was taken (WP-COLLECT-6, docs/capture-protocol.md).
 *
 * A phone photograph is an RGB observation. It is not a wavelength-resolved spectrum, and this
 * block carries no soil-property value of any kind (SPEC L1, section 17 K1). Every field is
 * something the person or the device stated about the capture. None of it is verified here,
 * and none of it can raise a provenance tier (SPEC I10).
 *
 * The block is private. It names a device and a time, so it never enters a public artifact
 * (SPEC I7); `pipeline/export.py` forbids the key.
 *
 * Every field is required, and a value that is not known is written as `null` or `unknown`,
 * never left out (SPEC L3). The block itself is optional wherever it is attached, so records
 * made before it existed still validate.
 */
import { z } from 'zod'

export const CAPTURE_ACQUISITION_VERSION = 'gsip-capture-acquisition-v1'
/** The written procedure this block describes: docs/capture-protocol.md. */
export const CAPTURE_STANDARD_VERSION = 'gsip-capture-standard-v1'
export const MAX_CAPTURE_ACQUISITION_BYTES = 8_000

// Short printable ASCII labels only: no free text, no line breaks, nothing that can hold a name.
const label = z
  .string()
  .min(1)
  .max(64)
  .regex(/^[0-9A-Za-z][0-9A-Za-z .,()+_/-]*$/)
const version = z
  .string()
  .min(1)
  .max(64)
  .regex(/^[0-9A-Za-z][0-9A-Za-z.+_-]*$/)
const cardId = z
  .string()
  .min(1)
  .max(48)
  .regex(/^[a-z0-9][a-z0-9-]*$/)
const cardVersion = z
  .string()
  .min(1)
  .max(24)
  .regex(/^[0-9A-Za-z][0-9A-Za-z.-]*$/)
const utcSecond = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?Z$/)
  .refine((value) => Number.isFinite(Date.parse(value)))
// A resolution-9 H3 cell: the grain GSIP already sends to outside processors (SPEC I7).
const h3Resolution9 = z.string().regex(/^89[0-9a-f]{13}$/)

export const LIGHTING_CONDITIONS = [
  'shade',
  'overcast',
  'diffuser',
  'direct_sun',
  'artificial',
  'unknown',
] as const
export const CAPTURE_PROCEDURES = [
  'prepared_sample',
  'field_profile',
  'unspecified',
] as const
export const CARD_DETECTIONS = ['not_run', 'none', 'one', 'multiple'] as const

const acquisition = z
  .strictObject({
    schema_version: z.literal(CAPTURE_ACQUISITION_VERSION),
    standard_version: z.literal(CAPTURE_STANDARD_VERSION),
    // I1: the only kind there is. A phone photograph is never recorded as a spectrum.
    observation_kind: z.literal('rgb_photo'),
    procedure: z.enum(CAPTURE_PROCEDURES),
    device: z.strictObject({
      make: label.nullable(),
      model: label.nullable(),
      os_name: label.nullable(),
      os_version: version.nullable(),
      app_version: version,
    }),
    camera: z.strictObject({
      exposure_time_s: z.number().finite().gt(0).max(30).nullable(),
      iso: z.number().int().min(1).max(1_000_000).nullable(),
      exposure: z.enum(['locked', 'auto', 'unknown']),
      white_balance: z.enum(['locked', 'auto', 'unknown']),
      hdr: z.enum(['off', 'on', 'unknown']),
      filters: z.enum(['off', 'on', 'unknown']),
      flash: z.enum(['off', 'on', 'unknown']),
      angle: z.enum(['nadir', 'oblique', 'unknown']),
      distance_cm: z.number().finite().min(1).max(500).nullable(),
      field_of_view_cm: z.number().finite().min(1).max(1_000).nullable(),
    }),
    lighting: z.enum(LIGHTING_CONDITIONS),
    reference_card: z.strictObject({
      detection: z.enum(CARD_DETECTIONS),
      card_id: cardId.nullable(),
      card_version: cardVersion.nullable(),
    }),
    calibration_status: z.enum(['uncalibrated', 'calibrated']),
    replicate_count: z.number().int().min(1).max(20).nullable(),
    captured_at: utcSecond,
    location: z.strictObject({
      consent: z.boolean(),
      h3_r9: h3Resolution9.nullable(),
    }),
  })
  // I3: only exactly one detected, identified card can make a capture `calibrated`.
  .refine(
    (value) =>
      value.calibration_status === 'uncalibrated' ||
      (value.reference_card.detection === 'one' &&
        value.reference_card.card_id !== null &&
        value.reference_card.card_version !== null),
  )
  // A card that was not detected has no identity to record.
  .refine(
    (value) =>
      value.reference_card.detection === 'one' ||
      (value.reference_card.card_id === null &&
        value.reference_card.card_version === null),
  )
  // I2: a place is recorded only with consent.
  .refine((value) => value.location.consent || value.location.h3_r9 === null)

/** Generic errors only: a rejected block's values and field names stay private. */
export const CaptureAcquisitionSchema = z
  .unknown()
  .transform((value, ctx): z.output<typeof acquisition> => {
    const result = acquisition.safeParse(value)
    if (!result.success) {
      ctx.addIssue({ code: 'custom', message: 'Invalid capture acquisition' })
      return z.NEVER
    }
    return result.data
  })

export type CaptureAcquisition = z.infer<typeof CaptureAcquisitionSchema>
export type CalibrationStatus = CaptureAcquisition['calibration_status']
export type CardDetection = CaptureAcquisition['reference_card']['detection']

export function parseCaptureAcquisition(raw: string): CaptureAcquisition {
  try {
    if (
      typeof raw !== 'string' ||
      raw.length > MAX_CAPTURE_ACQUISITION_BYTES ||
      new globalThis.TextEncoder().encode(raw).byteLength >
        MAX_CAPTURE_ACQUISITION_BYTES
    )
      throw new Error('too large')
    return CaptureAcquisitionSchema.parse(JSON.parse(raw))
  } catch {
    throw new Error('Invalid capture acquisition')
  }
}

/**
 * The card gate (I3). A capture is `calibrated` only when a detector found exactly one
 * reference card and could name its edition and version. A card the person says they used, a
 * card that was not looked for, no card and two cards are all `uncalibrated`.
 */
export function cardGate(finding: {
  detection: CardDetection
  cardId?: string | null
  cardVersion?: string | null
}): Pick<CaptureAcquisition, 'calibration_status' | 'reference_card'> {
  const identified =
    finding.detection === 'one' &&
    cardId.safeParse(finding.cardId).success &&
    cardVersion.safeParse(finding.cardVersion).success
  return {
    calibration_status: identified ? 'calibrated' : 'uncalibrated',
    reference_card: {
      detection: finding.detection,
      card_id: identified ? (finding.cardId ?? null) : null,
      card_version: identified ? (finding.cardVersion ?? null) : null,
    },
  }
}

/**
 * Split records for export so that the two kinds never share a list (I3). A record with no
 * acquisition block was made before the block existed and is uncalibrated.
 */
export function partitionByCalibration<
  Record extends { acquisition?: CaptureAcquisition | null },
>(
  records: readonly Record[],
): { calibrated: Record[]; uncalibrated: Record[] } {
  const calibrated: Record[] = []
  const uncalibrated: Record[] = []
  for (const record of records) {
    const status = record.acquisition
      ? CaptureAcquisitionSchema.parse(record.acquisition).calibration_status
      : 'uncalibrated'
    ;(status === 'calibrated' ? calibrated : uncalibrated).push(record)
  }
  return { calibrated, uncalibrated }
}
