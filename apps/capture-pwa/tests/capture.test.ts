import { afterEach, describe, expect, it, vi } from 'vitest'
import { captureTime, isCaptureLive } from '../src/capture'

const NOW = Date.parse('2026-10-10T12:00:00Z')

afterEach(() => vi.unstubAllEnvs())

describe('capture time', () => {
  it('uses the device timestamp of shot B', () => {
    const file = new File(['jpeg'], 'b.jpg', {
      lastModified: Date.parse('2026-10-08T07:30:00Z'),
      type: 'image/jpeg',
    })
    expect(captureTime(file, NOW)).toBe('2026-10-08T07:30:00.000Z')
  })

  it('falls back to now for missing, future or implausible timestamps', () => {
    const future = new File(['jpeg'], 'b.jpg', {
      lastModified: NOW + 60 * 60_000,
      type: 'image/jpeg',
    })
    const ancient = new File(['jpeg'], 'b.jpg', {
      lastModified: 0,
      type: 'image/jpeg',
    })
    expect(captureTime(null, NOW)).toBe('2026-10-10T12:00:00.000Z')
    expect(captureTime(future, NOW)).toBe('2026-10-10T12:00:00.000Z')
    expect(captureTime(ancient, NOW)).toBe('2026-10-10T12:00:00.000Z')
  })

  it('clamps small clock skew to now', () => {
    const skewed = new File(['jpeg'], 'b.jpg', {
      lastModified: NOW + 60_000,
      type: 'image/jpeg',
    })
    expect(captureTime(skewed, NOW)).toBe('2026-10-10T12:00:00.000Z')
  })
})

describe('capture launch flag', () => {
  it('is closed unless the build sets VITE_CAPTURE_LIVE=true', () => {
    expect(isCaptureLive()).toBe(false)
    vi.stubEnv('VITE_CAPTURE_LIVE', 'yes')
    expect(isCaptureLive()).toBe(false)
    vi.stubEnv('VITE_CAPTURE_LIVE', 'true')
    expect(isCaptureLive()).toBe(true)
  })
})
