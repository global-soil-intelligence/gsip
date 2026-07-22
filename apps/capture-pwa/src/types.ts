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
  queuedAt: string
}
