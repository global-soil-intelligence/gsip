import { describe, expect, it } from 'vitest'
import { GSIP_SPEC_VERSION } from '../src/index'

describe('schema package', () => {
  it('tracks the governing specification', () => {
    expect(GSIP_SPEC_VERSION).toBe('2.2')
  })
})
