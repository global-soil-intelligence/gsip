import type { GsipClient, ServiceState } from './supabase'

/** Collection mode is a build contract; the server remains the admission authority. */
export function isInvitedPilot(): boolean {
  return import.meta.env.VITE_COLLECTION_MODE === 'invited_private'
}

/** Explicit recovery/withdrawal view; loading an ordinary closed page never starts auth. */
export function isRightsView(native: boolean): boolean {
  return (
    !native &&
    (window.location.hash === '#your-data' ||
      new URLSearchParams(window.location.search).get('view') === 'your-data')
  )
}

export async function pilotOwner(client: GsipClient): Promise<string | null> {
  try {
    const { data, error } = await client.auth.getUser()
    const user = data.user
    return !error && user?.id && user.is_anonymous === false ? user.id : null
  } catch {
    return null
  }
}

/** Unknown/extra fields cannot silently authorize a newer or differently scoped service. */
export async function fetchPilotAdmission(
  client: GsipClient,
): Promise<ServiceState> {
  try {
    const { data, error } = await client.rpc('collection_pilot_capabilities')
    if (error || !data || typeof data !== 'object' || Array.isArray(data))
      return 'unknown'
    const value = data as Record<string, unknown>
    const keys = [
      'version',
      'mode',
      'member',
      'capture_open',
      'library_intake_available',
      'publication_held',
    ]
    if (
      Object.keys(value).length !== keys.length ||
      keys.some((key) => !(key in value)) ||
      value.version !== 'gsip-invited-pilot-v1' ||
      value.mode !== 'invited_private' ||
      value.publication_held !== true ||
      ['member', 'capture_open', 'library_intake_available'].some(
        (key) => typeof value[key] !== 'boolean',
      )
    )
      return 'unknown'
    return value.member && value.capture_open && value.library_intake_available
      ? 'open'
      : 'closed'
  } catch {
    return 'unknown'
  }
}

/** Permit only this page's known return paths, never arbitrary query/fragment redirects. */
export function existingAccountReturnUrl(rights: boolean): string {
  return `${window.location.origin}${window.location.pathname}${rights ? '?view=your-data#your-data' : ''}`
}

export function validExistingAccountReturnUrl(value: string): boolean {
  try {
    const url = new URL(value)
    return (
      url.origin === window.location.origin &&
      url.pathname === window.location.pathname &&
      ['', '?view=your-data'].includes(url.search) &&
      ['', '#your-data'].includes(url.hash) &&
      !url.username &&
      !url.password
    )
  } catch {
    return false
  }
}
