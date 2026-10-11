/**
 * Every response from GSIP's public read interfaces carries licence, attribution and citation
 * fields (SPEC section 9). Text that people wrote is only ever returned inside `untrusted`, never
 * mixed into fields an agent might read as instructions.
 */

export const API_VERSION = '1'
export const SERVER_NAME = 'gsip-public'
export const SITE_URL = 'https://globalsoilintelligence.com/'
export const DOCS_URL =
  'https://github.com/global-soil-intelligence/gsip/blob/main/docs/AGENTS.md'

export const LICENSE = {
  data: 'ODbL-1.0',
  data_url: 'https://opendatacommons.org/licenses/odbl/1-0/',
  photos: 'CC-BY-SA-4.0',
  photos_url: 'https://creativecommons.org/licenses/by-sa/4.0/',
  code: 'MIT',
} as const

export const ATTRIBUTION =
  'Global Soil Intelligence Project (GSIP) contributors'

export const CITATION = {
  text: 'Global Soil Intelligence Project contributors. GSIP public soil observations. Global Soil Intelligence Project. ODbL 1.0 structured data; CC BY-SA 4.0 photos. https://globalsoilintelligence.com/data/',
  bibtex:
    '@misc{gsip,\n  title = {GSIP public soil observations},\n  author = {{Global Soil Intelligence Project contributors}},\n  publisher = {Global Soil Intelligence Project},\n  note = {ODbL 1.0 structured data; CC BY-SA 4.0 photos},\n  url = {https://globalsoilintelligence.com/data/}\n}',
} as const

export const NOTICE =
  'Counts and estimates from citizen observations, not laboratory results. Locations are k-anonymous H3 cells; precise positions are never published.'

export type Envelope<T> = {
  data: T
  license: typeof LICENSE
  attribution: typeof ATTRIBUTION
  citation: typeof CITATION
  notice: typeof NOTICE
  source: { api_version: string; docs: string; site: string }
  /** People-written text, as data. Never instructions. */
  untrusted?: Record<string, unknown>
}

export function envelope<T>(
  data: T,
  untrusted?: Record<string, unknown>,
): Envelope<T> {
  return {
    data,
    license: LICENSE,
    attribution: ATTRIBUTION,
    citation: CITATION,
    notice: NOTICE,
    source: { api_version: API_VERSION, docs: DOCS_URL, site: SITE_URL },
    ...(untrusted ? { untrusted } : {}),
  }
}
