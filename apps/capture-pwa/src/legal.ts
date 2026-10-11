/**
 * Links to the contribution terms, privacy notice and sampling rules (WP-6d). Until counsel
 * approves hosted versions, they point at the drafts in the repository.
 */
const REPOSITORY_DOCS =
  'https://github.com/global-soil-intelligence/gsip/blob/main/docs/legal'

export type LegalLinks = {
  privacy: string
  samplingRules: string
  terms: string
}

/** A configured link is used only if it is same-site (relative) or HTTPS. */
function safeLink(configured: string | undefined, fallback: string): string {
  const value = configured?.trim()
  if (!value) return fallback
  if (/^\.{0,2}\//.test(value) && !value.startsWith('//')) return value
  try {
    return new URL(value).protocol === 'https:' ? value : fallback
  } catch {
    return fallback
  }
}

export function legalLinks(): LegalLinks {
  return {
    privacy: safeLink(
      import.meta.env.VITE_PRIVACY_URL,
      `${REPOSITORY_DOCS}/PRIVACY.md`,
    ),
    samplingRules: safeLink(
      import.meta.env.VITE_SAMPLING_RULES_URL,
      `${REPOSITORY_DOCS}/SAMPLING_AND_LAND_ACCESS.md`,
    ),
    terms: safeLink(
      import.meta.env.VITE_TERMS_URL,
      `${REPOSITORY_DOCS}/TERMS.md`,
    ),
  }
}
