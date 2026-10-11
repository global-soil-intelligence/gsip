import { isNativeApp } from './platform'
import { siteLink } from './platform/links'

/**
 * Links to the contribution terms, privacy notice and sampling rules (WP-6d). Until counsel
 * approves hosted versions, they point at the drafts in the repository.
 */
const REPOSITORY_DOCS =
  'https://github.com/global-soil-intelligence/gsip/blob/main/docs/legal'
// A stand-in origin to resolve relative links against: a same-site link keeps this origin.
const PROBE_ORIGIN = 'https://same-site.invalid'

export type LegalLinks = {
  privacy: string
  samplingRules: string
  terms: string
}

/**
 * A configured link is used only if it is HTTPS or genuinely same-site. Relative values are
 * resolved the way a browser would, so `/\\host`, `//host` or a path with a tab in it cannot turn
 * into a link to another site.
 */
function safeLink(configured: string | undefined, fallback: string): string {
  const value = configured?.trim()
  if (!value) return fallback
  try {
    if (/^[a-z][a-z0-9+.-]*:/i.test(value))
      return new URL(value).protocol === 'https:' ? value : fallback
    const resolved = new URL(value, `${PROBE_ORIGIN}/app/`)
    return resolved.origin === PROBE_ORIGIN && !/[\s\\]/.test(value)
      ? value
      : fallback
  } catch {
    return fallback
  }
}

/** In the phone app a same-site link points at the public site, where the documents live. */
export function legalLinks(native: boolean = isNativeApp()): LegalLinks {
  const link = (configured: string | undefined, fallback: string) =>
    siteLink(safeLink(configured, fallback), native)
  return {
    privacy: link(
      import.meta.env.VITE_PRIVACY_URL,
      `${REPOSITORY_DOCS}/PRIVACY.md`,
    ),
    samplingRules: link(
      import.meta.env.VITE_SAMPLING_RULES_URL,
      `${REPOSITORY_DOCS}/SAMPLING_AND_LAND_ACCESS.md`,
    ),
    terms: link(import.meta.env.VITE_TERMS_URL, `${REPOSITORY_DOCS}/TERMS.md`),
  }
}
