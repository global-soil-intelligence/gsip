/**
 * `gsip-public` reads only as the database's anonymous role (SPEC I12). These helpers find the
 * project's publishable key in the platform's environment and recognize no other kind of key, so
 * a misconfigured deployment fails closed instead of reading with more privilege.
 */

type Env = (name: string) => string | undefined

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function base64UrlDecode(segment: string): string {
  const base64 = segment.replace(/-/g, '+').replace(/_/g, '/')
  const padded = base64.padEnd(
    base64.length + ((4 - (base64.length % 4)) % 4),
    '=',
  )
  const bytes = Uint8Array.from(atob(padded), (char) => char.charCodeAt(0))
  return new TextDecoder('utf-8', { fatal: true }).decode(bytes)
}

/**
 * True for a publishable key (`sb_publishable_…`) or a legacy anonymous JWT (role `anon`). The JWT
 * is not verified here; PostgREST verifies it. This only refuses keys that claim another role.
 */
export function isPublishableKey(key: string): boolean {
  if (/^sb_publishable_[A-Za-z0-9_-]+$/.test(key)) return true
  const parts = key.split('.')
  if (parts.length !== 3 || !parts[1]) return false
  try {
    const payload: unknown = JSON.parse(base64UrlDecode(parts[1]))
    return isObject(payload) && payload.role === 'anon'
  } catch {
    return false
  }
}

/**
 * The publishable key from the Edge Function environment: `SUPABASE_PUBLISHABLE_KEYS` (a JSON
 * object of named keys, `default` first) on hosted projects, then `SUPABASE_PUBLISHABLE_KEY` or
 * the legacy `SUPABASE_ANON_KEY`. Anything that is not a publishable key is skipped.
 */
export function publishableKeyFrom(env: Env): string | undefined {
  const candidates: unknown[] = []
  const named = env('SUPABASE_PUBLISHABLE_KEYS')
  if (named) {
    try {
      const keys: unknown = JSON.parse(named)
      if (isObject(keys)) candidates.push(keys.default, ...Object.values(keys))
    } catch {
      // A malformed value is ignored; the single-key variables below may still be set.
    }
  }
  candidates.push(env('SUPABASE_PUBLISHABLE_KEY'), env('SUPABASE_ANON_KEY'))
  for (const candidate of candidates) {
    if (typeof candidate !== 'string') continue
    const key = candidate.trim()
    if (isPublishableKey(key)) return key
  }
  return undefined
}
