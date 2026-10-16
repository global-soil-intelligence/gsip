import { afterEach, expect, it, vi } from 'vitest'
import {
  fetchPilotAdmission,
  isInvitedPilot,
  isRightsView,
  pilotOwner,
} from '../src/pilot'
import type { GsipClient } from '../src/supabase'

const capabilities = {
  version: 'gsip-invited-pilot-v1',
  mode: 'invited_private',
  member: true,
  capture_open: true,
  library_intake_available: true,
  publication_held: true,
}
function client(data: unknown, error: unknown = null) {
  return {
    rpc: vi.fn(async () => ({ data, error })),
  } as unknown as GsipClient
}
afterEach(() => {
  vi.unstubAllEnvs()
  window.history.replaceState(null, '', '/')
})
it.each([undefined, '', 'public', 'invited_private '])(
  'keeps unknown/missing collection mode %s closed',
  (mode) => {
    vi.stubEnv('VITE_COLLECTION_MODE', mode)
    expect(isInvitedPilot()).toBe(false)
  },
)
it('requires the exact invited mode and explicit browser rights fragment', () => {
  vi.stubEnv('VITE_COLLECTION_MODE', 'invited_private')
  expect(isInvitedPilot()).toBe(true)
  window.location.hash = '#your-data'
  expect(isRightsView(false)).toBe(true)
  expect(isRightsView(true)).toBe(false)
  window.location.hash = '#your-data-extra'
  expect(isRightsView(false)).toBe(false)
})
it('accepts only the complete current held-publication admission contract', async () => {
  const c = client(capabilities)
  expect(await fetchPilotAdmission(c)).toBe('open')
  expect(c.rpc).toHaveBeenCalledWith('collection_pilot_capabilities')
})
it.each(['member', 'capture_open', 'library_intake_available'])(
  'holds a valid closed %s without treating it as admission',
  async (key) => {
    expect(
      await fetchPilotAdmission(client({ ...capabilities, [key]: false })),
    ).toBe('closed')
  },
)
it.each([
  null,
  [],
  { ...capabilities, version: 'future' },
  { ...capabilities, mode: 'public' },
  { ...capabilities, publication_held: false },
  { ...capabilities, member: 'true' },
  { ...capabilities, private_identity: 'must-not-be-returned' },
  Object.fromEntries(
    Object.entries(capabilities).filter(([key]) => key !== 'member'),
  ),
])(
  'refuses absent, incompatible or authority-bearing capabilities',
  async (value) => {
    expect(await fetchPilotAdmission(client(value))).toBe('unknown')
  },
)
it('holds unavailable admission instead of surfacing private failure details', async () => {
  expect(await fetchPilotAdmission(client(null, new Error('private')))).toBe(
    'unknown',
  )
  const c = {
    rpc: async () => {
      throw new Error('private')
    },
  } as unknown as GsipClient
  expect(await fetchPilotAdmission(c)).toBe('unknown')
})
it.each([null, { id: 'owner' }, { id: 'owner', is_anonymous: true }])(
  'refuses missing or anonymous identities without creating an account',
  async (user) => {
    const auth = {
      getUser: vi.fn(async () => ({ data: { user }, error: null })),
      signInAnonymously: vi.fn(),
    }
    expect(await pilotOwner({ auth } as unknown as GsipClient)).toBeNull()
    expect(auth.signInAnonymously).not.toHaveBeenCalled()
  },
)
it('requires a fresh existing non-anonymous account', async () => {
  const auth = {
    getUser: vi.fn(async () => ({
      data: { user: { id: 'owner', is_anonymous: false } },
      error: null,
    })),
  }
  expect(await pilotOwner({ auth } as unknown as GsipClient)).toBe('owner')
  expect(auth.getUser).toHaveBeenCalledOnce()
})
