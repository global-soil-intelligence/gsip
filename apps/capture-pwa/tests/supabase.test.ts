import { describe, expect, it } from 'vitest'
import { photoStoragePath } from '../src/supabase'
import type { QueueRecord } from '../src/types'

describe('hosted submission paths', () => {
  it('keeps uploads beneath the authenticated owner prefix', () => {
    const record = {
      photos: [{ objectId: 'photo-id', shotType: 'B' }],
      submissionId: 'submission-id',
    } as QueueRecord

    expect(photoStoragePath('user-id', record, record.photos[0])).toBe(
      'user-id/submission-id/B/photo-id.jpg',
    )
  })
})
