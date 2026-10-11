/**
 * Public attribution names are published with every released photo, so they are an abuse and
 * prompt-injection channel. These rules mirror the database constraint
 * `contribution_grants_attribution_safe` (WP-6b): a client must refuse a name the database
 * would reject, or the queued observation could never sync.
 */

export const DEFAULT_ATTRIBUTION = 'Anonymous soil contributor'
export const ATTRIBUTION_MAX_LENGTH = 80

export type AttributionProblem =
  'empty' | 'too_long' | 'surrounding_space' | 'characters' | 'link'

const MARKUP_CHARACTERS = new Set('<>{}[]\\`|^~$*=#@')
const LINK_PATTERN = /([a-z][a-z0-9+.-]*:\/\/|www\.)/i

function isControl(codePoint: number): boolean {
  return codePoint < 0x20 || (codePoint >= 0x7f && codePoint <= 0x9f)
}

export function attributionProblem(name: string): AttributionProblem | null {
  if (name.length === 0) return 'empty'
  if ([...name].length > ATTRIBUTION_MAX_LENGTH) return 'too_long'
  if (name !== name.trim()) return 'surrounding_space'
  for (const character of name) {
    const codePoint = character.codePointAt(0) ?? 0
    if (isControl(codePoint) || MARKUP_CHARACTERS.has(character))
      return 'characters'
  }
  if (LINK_PATTERN.test(name)) return 'link'
  return null
}

export function normalizeAttribution(input: string): string {
  const trimmed = input.trim().replace(/\s+/g, ' ')
  return trimmed || DEFAULT_ATTRIBUTION
}
