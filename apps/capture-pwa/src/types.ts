import type { QueuedLibrary } from './library'
import type { ProvenanceClaims } from './provenance'

export type ShotType = 'A' | 'B' | 'C'

export type QueuedPhoto = {
  bytes: Uint8Array
  mimeType: string
  objectId: string
  shotType: ShotType
}

export type CaptureDraft = {
  /** Local transport fence only. The server independently assigns immutable collection scope. */
  collectionMode?: 'invited_private'
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
  /** Optional private intake; its presence can never fall back to ordinary capture. */
  library?: QueuedLibrary
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
  /** Immutable library identity/context refusal: only local discard, never new IDs on retry. */
  libraryConflictAt?: string
  queuedAt: string
  /**
   * When the person accepted the current terms again for an observation whose original acceptance
   * expired (I9). The original `acceptedAt` is kept: it is always offered to the server first, so
   * an observation its person withdrew is refused as withdrawn and dropped, never re-accepted.
   */
  reconfirmedAt?: string
  reconfirmedTermsVersion?: string
  syncAttempts?: number
  /** Set when its terms acceptance is too old to record: kept, not sent, until accepted again. */
  termsExpiredAt?: string
}
