import { describe, expect, it } from 'vitest'
import { isPublishableKey, publishableKeyFrom } from '../../src/agent/keys'
import { postgrestReader } from '../../src/agent/reader'

function base64Url(text: string): string {
  return btoa(text).replace(/=+$/, '').replace(/\+/g, '-').replace(/\//g, '_')
}

/** An unsigned JWT-shaped key claiming `role`; PostgREST, not GSIP, verifies signatures. */
function legacyKey(role: string): string {
  return [
    base64Url(JSON.stringify({ alg: 'HS256', typ: 'JWT' })),
    base64Url(JSON.stringify({ iss: 'supabase', role })),
    'signature',
  ].join('.')
}

const PUBLISHABLE = 'sb_publishable_' + '0'.repeat(32)
const env =
  (values: Record<string, string>) =>
  (name: string): string | undefined =>
    values[name]

describe('the function holds only a publishable key (I12)', () => {
  it('recognizes publishable and legacy anonymous keys, and nothing else', () => {
    expect(isPublishableKey(PUBLISHABLE)).toBe(true)
    expect(isPublishableKey(legacyKey('anon'))).toBe(true)
    for (const key of [
      'sb_secret_' + '0'.repeat(32),
      legacyKey('authenticated'),
      legacyKey('service_role'),
      'not.a.jwt',
      'sb_publishable_',
      '',
    ]) {
      expect(isPublishableKey(key), key).toBe(false)
    }
  })

  it('takes the default publishable key a hosted project provides', () => {
    expect(
      publishableKeyFrom(
        env({
          SUPABASE_PUBLISHABLE_KEYS: JSON.stringify({
            default: PUBLISHABLE,
            mobile: 'sb_publishable_' + '1'.repeat(32),
          }),
          SUPABASE_ANON_KEY: legacyKey('anon'),
        }),
      ),
    ).toBe(PUBLISHABLE)
    expect(
      publishableKeyFrom(
        env({
          SUPABASE_PUBLISHABLE_KEYS: JSON.stringify({ web: PUBLISHABLE }),
        }),
      ),
    ).toBe(PUBLISHABLE)
  })

  it('falls back to the single-key variables and skips anything privileged', () => {
    expect(
      publishableKeyFrom(
        env({
          SUPABASE_PUBLISHABLE_KEYS: '{not json',
          SUPABASE_PUBLISHABLE_KEY: 'sb_secret_' + '0'.repeat(32),
          SUPABASE_ANON_KEY: legacyKey('anon'),
        }),
      ),
    ).toBe(legacyKey('anon'))
    expect(
      publishableKeyFrom(
        env({ SUPABASE_PUBLISHABLE_KEYS: JSON.stringify({ default: 42 }) }),
      ),
    ).toBeUndefined()
    expect(
      publishableKeyFrom(env({ SUPABASE_ANON_KEY: legacyKey('service_role') })),
    ).toBeUndefined()
  })

  it('refuses to build a reader with any other key', () => {
    expect(() =>
      postgrestReader({
        url: 'https://project.supabase.co',
        publishableKey: legacyKey('authenticated'),
      }),
    ).toThrow(/publishable key/)
  })
})
