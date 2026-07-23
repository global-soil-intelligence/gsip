export type ShotType = 'A' | 'B' | 'C'

export type QueuedPhoto = {
  bytes: Uint8Array
  mimeType: string
  objectId: string
  shotType: ShotType
}

export type CaptureDraft = {
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
  draft?: boolean
  ownerId?: string
  deadLetteredAt?: string
  nextRetryAt?: string
  queuedAt: string
  syncAttempts?: number
}

export type ObservationReceipt = {
  submissionId: string
  capturedAt: string
  h3R8: string
  status: string
}
