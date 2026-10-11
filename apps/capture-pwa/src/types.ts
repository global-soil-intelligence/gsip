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
  deviceModel: string
  disturbed: boolean
  grantId: string
  landCover: string
  latitude: number
  longitude: number
  photos: QueuedPhoto[]
  submissionId: string
  surfaceCondition: string
  termsVersion: string
}

export type QueueRecord = CaptureDraft & {
  deadLetteredAt?: string
  nextRetryAt?: string
  queuedAt: string
  syncAttempts?: number
}
