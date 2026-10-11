/** The contribution terms version this build presents; it is published in `terms_versions`. */
export const TERMS_VERSION = '2026-07-22-v1'

/** The server records a grant only if its terms were accepted within the last 30 days (I9). */
export const ACCEPTANCE_WINDOW_MS = 30 * 24 * 60 * 60_000
// Hold a record an hour early, so transit time and small clock differences never cross the line.
const ACCEPTANCE_MARGIN_MS = 60 * 60_000

/**
 * True when an observation waited so long to sync that the server would no longer record its
 * terms acceptance. Such a record is held until the person accepts the terms again; an
 * unreadable acceptance time counts as expired.
 */
export function acceptanceExpired(
  acceptedAt: string | undefined,
  now: number,
): boolean {
  const accepted = acceptedAt ? Date.parse(acceptedAt) : Number.NaN
  return (
    !Number.isFinite(accepted) ||
    accepted < now - (ACCEPTANCE_WINDOW_MS - ACCEPTANCE_MARGIN_MS)
  )
}
