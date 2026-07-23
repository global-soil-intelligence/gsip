import { beforeEach, vi } from 'vitest'
vi.mock('../../map-web/src/App', () => ({ App: () => null }))
beforeEach(() => {
  vi.stubEnv('VITE_CAPTURE_LIVE', 'true')
  URL.createObjectURL = vi.fn(() => 'blob:test-photo')
  URL.revokeObjectURL = vi.fn()
})
