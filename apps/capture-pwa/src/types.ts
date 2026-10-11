import type { ProvenanceClaims } from './provenance'

export type ShotType = 'A' | 'B' | 'C'

export type QueuedPhoto = {
  bytes: Uint8Array
  mimeType: string
  objectId: string
  shotType: ShotType
}

export type CaptureDraft = {
  /** When the person accepted the terms (submit time); records from older builds lack it. */
  acceptedAt?: string
  accuracyM: number | null
  attributionName: string
  capturedAt: string
  /** WP-6e: how the app says the observation was made; records from older builds lack it. */
  claims?: ProvenanceClaims
  deviceModel: string
  disturbed: boolean
  grantId: string
  landCover: string
  latitude: number
  longitude: number
  /** The auth user signed in when the observation was queued; it is only ever sent as them. */
  ownerUid?: string
  photos: QueuedPhoto[]
  submissionId: string
  surfaceCondition: string
  termsVersion: string
}

export type QueueRecord = CaptureDraft & {
  deadLetteredAt?: string
  /** Set when its account is no longer signed in here: kept, not sent, until the person decides. */
  heldAt?: string
  nextRetryAt?: string
  queuedAt: string
  syncAttempts?: number
  /** Set when its terms acceptance is too old to record: kept, not sent, until accepted again. */
  termsExpiredAt?: string
}
