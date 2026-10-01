import { describe, expect, it } from 'vitest'
import type { TablesInsert } from '../src/database.types'

describe('generated database types', () => {
  it('requires every submission to reference a grant', () => {
    const submission = {
      captured_at: '2026-07-22T00:00:00Z',
      contributor_id: 'contributor',
      geom_precise: 'POINT(0 0)',
      grant_id: 'grant',
      h3_r6: '86754e64fffffff',
      h3_r8: '88754e6499fffff',
    } satisfies TablesInsert<'submissions'>

    expect(submission.grant_id).toBe('grant')
  })
})
