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
import { rejectDuplicateKeys } from './libraryIntake.ts'

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
// Only the two GSIP editions `pipeline/cards.py` can read. Nothing else can be named.
export const CARD_EDITIONS = { 'gsip-a6': 'v1', 'gsip-node': 'v1' } as const
const cardId = z.enum(['gsip-a6', 'gsip-node'])
const cardVersion = z.literal('v1')
// A real UTC calendar second from year 0001 on. `Date.parse` alone rolls 30 February over.
const utcSecond = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?Z$/)
  .refine((value) => {
    const parsed = Date.parse(value)
    return (
      Number.isFinite(parsed) &&
      !value.startsWith('0000') &&
      new Date(parsed).toISOString().slice(0, 19) === value.slice(0, 19)
    )
  })
// A resolution-9 H3 cell: the grain GSIP already sends to outside processors (SPEC I7).
// At resolution 9 the six unused digits are all ones, which fixes the last 18 bits.
const h3Resolution9 = z.string().regex(/^89[0-9a-f]{8}[37bf]ffff$/)

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
    rejectDuplicateKeys(raw)
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
  const id = cardId.safeParse(finding.cardId)
  const edition = cardVersion.safeParse(finding.cardVersion)
  const identified =
    finding.detection === 'one' && id.success && edition.success
  return {
    calibration_status: identified ? 'calibrated' : 'uncalibrated',
    reference_card: {
      detection: finding.detection,
      card_id: identified ? id.data : null,
      card_version: identified ? edition.data : null,
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
    const status =
      record.acquisition === undefined || record.acquisition === null
        ? 'uncalibrated'
        : CaptureAcquisitionSchema.parse(record.acquisition).calibration_status
    ;(status === 'calibrated' ? calibrated : uncalibrated).push(record)
  }
  return { calibrated, uncalibrated }
}
