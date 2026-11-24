/**
 * WP-COLLECT-6: the capture-time checklist and the card gate (docs/capture-protocol.md).
 *
 * What the checklist records is what the person says about how the photo was taken. The app
 * cannot see camera settings: it reads no exposure time or ISO, and it does not control white
 * balance, HDR or flash. Those stay `unknown` unless the person ticks them.
 *
 * The acquisition block is kept with the observation on this device. Nothing sends it yet: the
 * service has no column for it, and adding one is a separate reviewed migration.
 */
import {
  CAPTURE_ACQUISITION_VERSION,
  CAPTURE_STANDARD_VERSION,
  type CaptureAcquisition,
  CaptureAcquisitionSchema,
  type CardDetection,
  cardGate,
} from '@gsip/schema'
import { latLngToCell } from 'h3-js'

export type Lighting = CaptureAcquisition['lighting']
export type Procedure = CaptureAcquisition['procedure']

/** The person's own statements. An unticked box means "not stated", never "it was on". */
export type CaptureChecklistState = {
  procedure: Procedure
  lighting: Lighting
  whiteBalanceLocked: boolean
  exposureLocked: boolean
  hdrOff: boolean
  filtersOff: boolean
  flashOff: boolean
  cameraSquare: boolean
  distanceCm: string
  fieldOfViewCm: string
  replicateCount: string
  /** Consent to keep an approximate area (about 0.1 km²) in the acquisition block. */
  shareArea: boolean
}

export const EMPTY_CHECKLIST: CaptureChecklistState = {
  procedure: 'unspecified',
  lighting: 'unknown',
  whiteBalanceLocked: false,
  exposureLocked: false,
  hdrOff: false,
  filtersOff: false,
  flashOff: false,
  cameraSquare: false,
  distanceCm: '',
  fieldOfViewCm: '',
  replicateCount: '',
  shareArea: false,
}

export const PROCEDURE_LABELS: Record<Procedure, string> = {
  unspecified: 'No standard procedure',
  prepared_sample: 'Prepared sample: air-dried, sieved to 2 mm, in a tray',
  field_profile: 'Field profile: cleaned face, card in the same plane',
}

export const LIGHTING_LABELS: Record<Lighting, string> = {
  unknown: 'Not stated',
  shade: 'Open shade',
  overcast: 'Overcast sky',
  diffuser: 'Under a diffuser',
  direct_sun: 'Direct sun',
  artificial: 'Indoor or artificial light',
}

export const CHECKLIST_ITEMS: ReadonlyArray<{
  key:
    | 'whiteBalanceLocked'
    | 'exposureLocked'
    | 'hdrOff'
    | 'filtersOff'
    | 'flashOff'
    | 'cameraSquare'
  label: string
}> = [
  { key: 'whiteBalanceLocked', label: 'White balance is locked' },
  { key: 'exposureLocked', label: 'Exposure is locked' },
  { key: 'hdrOff', label: 'HDR is off' },
  { key: 'filtersOff', label: 'Filters, scene and portrait modes are off' },
  { key: 'flashOff', label: 'Flash is off' },
  {
    key: 'cameraSquare',
    label: 'The camera points straight at the soil, square to its surface',
  },
]

/** What a card detector reports about one photograph. */
export type CardFinding = {
  detection: CardDetection
  cardId?: string | null
  cardVersion?: string | null
}

/**
 * Looks for a reference card in a photograph. A detector that needs time (a worker, a compiled
 * module) will need this to become asynchronous and to run before the observation is queued.
 */
export type CardDetector = {
  readonly name: string
  detect(photo: Uint8Array): CardFinding
}

/**
 * STUB. The app has no card detector: reading the card's marker needs an image library the app
 * does not ship, and a new dependency needs its own review. This detector looks at nothing and
 * always answers `not_run`, so every observation queued by the app is `uncalibrated`. The
 * server's photo checks (`pipeline/qa_cards.py`) remain the only place a card is read.
 */
export const stubCardDetector: CardDetector = {
  name: 'stub-not-run',
  detect: () => ({ detection: 'not_run' }),
}

function bounded(
  text: string,
  minimum: number,
  maximum: number,
): number | null {
  if (!text.trim()) return null
  const value = Number(text)
  return Number.isFinite(value) && value >= minimum && value <= maximum
    ? value
    : null
}

function wholeNumber(text: string, minimum: number, maximum: number) {
  const value = bounded(text, minimum, maximum)
  return value !== null && Number.isInteger(value) ? value : null
}

/** Only the operating-system family: the app asks for no model, build or serial. */
export function osFamily(userAgent: string): string | null {
  if (/iPhone|iPad|iPod/i.test(userAgent)) return 'iOS'
  // Android browsers also say "Linux", so Android is looked for first.
  if (/Android/i.test(userAgent)) return 'Android'
  if (/Macintosh/i.test(userAgent)) return 'macOS'
  return userAgent.match(/Windows|Linux/i)?.[0] ?? null
}

function timestamp(capturedAt: string, now: number): string {
  const parsed = Date.parse(capturedAt)
  const iso = new Date(Number.isFinite(parsed) ? parsed : now).toISOString()
  // Years outside 0001 to 9999 print in a longer form the record does not accept.
  return /^(?!0000)\d{4}-/.test(iso) ? iso : new Date(now).toISOString()
}

function areaCell(
  share: boolean,
  latitude: number | null | undefined,
  longitude: number | null | undefined,
): string | null {
  if (
    !share ||
    typeof latitude !== 'number' ||
    typeof longitude !== 'number' ||
    !Number.isFinite(latitude) ||
    !Number.isFinite(longitude) ||
    Math.abs(latitude) > 90 ||
    Math.abs(longitude) > 180
  )
    return null
  try {
    return latLngToCell(latitude, longitude, 9)
  } catch {
    return null
  }
}

export type AcquisitionInput = {
  checklist: CaptureChecklistState
  appVersion: string
  capturedAt: string
  /** Shot B, the primary photograph: the card gate looks at this one. */
  photo: Uint8Array
  latitude?: number | null
  longitude?: number | null
  userAgent?: string
  detector?: CardDetector
  now?: number
}

/** Nothing stated, nothing read: valid whatever went wrong while building the real block. */
function minimalAcquisition(): CaptureAcquisition {
  return CaptureAcquisitionSchema.parse({
    schema_version: CAPTURE_ACQUISITION_VERSION,
    standard_version: CAPTURE_STANDARD_VERSION,
    observation_kind: 'rgb_photo',
    procedure: 'unspecified',
    device: {
      make: null,
      model: null,
      os_name: null,
      os_version: null,
      app_version: 'unknown',
    },
    camera: {
      exposure_time_s: null,
      iso: null,
      exposure: 'unknown',
      white_balance: 'unknown',
      hdr: 'unknown',
      filters: 'unknown',
      flash: 'unknown',
      angle: 'unknown',
      distance_cm: null,
      field_of_view_cm: null,
    },
    lighting: 'unknown',
    ...cardGate({ detection: 'not_run' }),
    replicate_count: null,
    captured_at: new Date(Date.now()).toISOString(),
    location: { consent: false, h3_r9: null },
  })
}

function statedAcquisition(input: AcquisitionInput): CaptureAcquisition {
  const { checklist } = input
  const now = Number.isFinite(input.now) ? (input.now as number) : Date.now()
  let finding: CardFinding
  try {
    finding = (input.detector ?? stubCardDetector).detect(input.photo)
  } catch {
    finding = { detection: 'not_run' }
  }
  const text = (value: unknown) => (typeof value === 'string' ? value : '')
  const shareArea = checklist.shareArea === true
  return CaptureAcquisitionSchema.parse({
    schema_version: CAPTURE_ACQUISITION_VERSION,
    standard_version: CAPTURE_STANDARD_VERSION,
    observation_kind: 'rgb_photo',
    procedure:
      checklist.procedure in PROCEDURE_LABELS
        ? checklist.procedure
        : 'unspecified',
    device: {
      make: null,
      model: null,
      os_name: osFamily(text(input.userAgent)),
      os_version: null,
      app_version: /^[0-9A-Za-z][0-9A-Za-z.+_-]{0,63}$/.test(input.appVersion)
        ? input.appVersion
        : 'unknown',
    },
    camera: {
      exposure_time_s: null,
      iso: null,
      exposure: checklist.exposureLocked === true ? 'locked' : 'unknown',
      white_balance:
        checklist.whiteBalanceLocked === true ? 'locked' : 'unknown',
      hdr: checklist.hdrOff === true ? 'off' : 'unknown',
      filters: checklist.filtersOff === true ? 'off' : 'unknown',
      flash: checklist.flashOff === true ? 'off' : 'unknown',
      angle: checklist.cameraSquare === true ? 'nadir' : 'unknown',
      distance_cm: bounded(text(checklist.distanceCm), 1, 500),
      field_of_view_cm: bounded(text(checklist.fieldOfViewCm), 1, 1_000),
    },
    lighting:
      checklist.lighting in LIGHTING_LABELS ? checklist.lighting : 'unknown',
    ...cardGate(finding ?? { detection: 'not_run' }),
    replicate_count: wholeNumber(text(checklist.replicateCount), 1, 20),
    captured_at: timestamp(text(input.capturedAt), now),
    location: {
      consent: shareArea,
      h3_r9: areaCell(shareArea, input.latitude, input.longitude),
    },
  })
}

/**
 * The acquisition block for a new observation. It never throws: a value the app cannot read
 * or the person did not state is written as `unknown` or `null`, and if building the block
 * fails for any reason the observation still gets a valid block that states nothing. The card
 * gate sets `calibration_status`; nothing the person ticks can make a capture `calibrated`.
 */
export function buildAcquisition(input: AcquisitionInput): CaptureAcquisition {
  try {
    return statedAcquisition(input)
  } catch {
    return minimalAcquisition()
  }
}

/** How many of the checklist's statements were made, for the summary line. */
export function checklistProgress(checklist: CaptureChecklistState): {
  done: number
  total: number
} {
  const stated = [
    checklist.procedure !== 'unspecified',
    checklist.lighting !== 'unknown',
    ...CHECKLIST_ITEMS.map(({ key }) => checklist[key]),
    bounded(checklist.distanceCm, 1, 500) !== null,
    wholeNumber(checklist.replicateCount, 1, 20) !== null,
  ]
  return { done: stated.filter(Boolean).length, total: stated.length }
}
