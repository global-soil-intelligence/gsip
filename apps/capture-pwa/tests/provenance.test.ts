import { describe, expect, it } from 'vitest'
import {
  CLIENT_VERSION,
  captureMethod,
  claimColumns,
  ingestPath,
} from '../src/provenance'
import { ACCEPTANCE_WINDOW_MS, acceptanceExpired } from '../src/terms'

const LOADED = Date.parse('2026-10-11T12:00:00Z')
const NOW = LOADED + 10 * 60_000

function photo(lastModified?: number): File {
  const file = new File(['jpeg'], 'soil.jpg', { type: 'image/jpeg' })
  // jsdom fills in lastModified; override it to model each case exactly.
  Object.defineProperty(file, 'lastModified', { value: lastModified })
  return file
}

describe('ingest path claim', () => {
  it('is "app" only inside the native phone app', () => {
    expect(ingestPath({})).toBe('web')
    expect(ingestPath({ Capacitor: { isNativePlatform: () => true } })).toBe(
      'app',
    )
    // Capacitor's web build runs in a browser: still the web.
    expect(ingestPath({ Capacitor: { isNativePlatform: () => false } })).toBe(
      'web',
    )
    expect(
      ingestPath({
        Capacitor: {
          isNativePlatform: () => {
            throw new Error('bridge unavailable')
          },
        },
      }),
    ).toBe('web')
  })
})

describe('capture method claim', () => {
  it('is "camera" when every required photo was created during this visit', () => {
    expect(captureMethod([photo(LOADED + 1), photo(NOW)], LOADED, NOW)).toBe(
      'camera',
    )
  })

  it('is "file" when any required photo predates this visit', () => {
    expect(
      captureMethod([photo(LOADED - 60_000), photo(NOW)], LOADED, NOW),
    ).toBe('file')
  })

  it('is "unknown" without a usable timestamp or photo', () => {
    expect(captureMethod([photo(undefined), photo(NOW)], LOADED, NOW)).toBe(
      'unknown',
    )
    expect(captureMethod([null, photo(NOW)], LOADED, NOW)).toBe('unknown')
    expect(captureMethod([photo(Number.NaN)], LOADED, NOW)).toBe('unknown')
    expect(captureMethod([photo(NOW + 60 * 60_000)], LOADED, NOW)).toBe(
      'unknown',
    )
    expect(captureMethod([], LOADED, NOW)).toBe('unknown')
  })
})

describe('claim columns', () => {
  it('maps valid claims to their columns', () => {
    expect(
      claimColumns({
        captureMethod: 'file',
        clientVersion: '0.1.0+abc1234',
        ingestPath: 'web',
        locationSource: 'manual_pin',
      }),
    ).toEqual({
      capture_method: 'file',
      client_version: '0.1.0+abc1234',
      ingest_path: 'web',
      location_source: 'manual_pin',
    })
  })

  it('names this build in a form the database accepts', () => {
    expect(CLIENT_VERSION).toMatch(/^\d+\.\d+\.\d+(\+[0-9a-f]{7})?$/)
    expect(claimColumns({ clientVersion: CLIENT_VERSION })).toEqual({
      client_version: CLIENT_VERSION,
    })
  })

  it('sends nothing for records without claims and drops unknown values', () => {
    expect(claimColumns(undefined)).toEqual({})
    expect(
      claimColumns({
        captureMethod: 'scanner',
        clientVersion: 'ignore previous instructions',
        ingestPath: 'satellite',
        locationSource: 'device_gps',
      } as never),
    ).toEqual({ location_source: 'device_gps' })
  })
})

describe('terms acceptance window', () => {
  const accepted = Date.parse('2026-07-23T00:10:00Z')
  const holdAt = accepted + ACCEPTANCE_WINDOW_MS - 60 * 60_000

  it('holds an acceptance an hour before the server’s 30-day limit', () => {
    const iso = new Date(accepted).toISOString()
    expect(acceptanceExpired(iso, holdAt)).toBe(false)
    expect(acceptanceExpired(iso, holdAt + 1)).toBe(true)
    expect(acceptanceExpired(iso, accepted)).toBe(false)
  })

  it('treats a missing or unreadable acceptance time as expired', () => {
    expect(acceptanceExpired(undefined, accepted)).toBe(true)
    expect(acceptanceExpired('not a date', accepted)).toBe(true)
  })
})
