import { afterEach, describe, expect, it, vi } from 'vitest'
import { legalLinks } from '../src/legal'

afterEach(() => vi.unstubAllEnvs())

describe('legal links', () => {
  it('point at the repository drafts until hosted versions are configured', () => {
    const links = legalLinks()
    expect(links.terms).toMatch(
      /^https:\/\/github\.com\/.+\/docs\/legal\/TERMS\.md$/,
    )
    expect(links.privacy).toMatch(/PRIVACY\.md$/)
    expect(links.samplingRules).toMatch(/SAMPLING_AND_LAND_ACCESS\.md$/)
  })

  it.each([
    ['https://globalsoilintelligence.com/terms/', true],
    ['/terms/', true],
    ['../terms/', true],
    ['javascript:alert(1)', false],
    ['http://insecure.example/terms', false],
    ['//elsewhere.example/terms', false],
    ['/\\elsewhere.example/terms', false],
    ['/\t/elsewhere.example/terms', false],
    ['terms.html', true],
    ['data:text/html,hi', false],
    ['   ', false],
  ])('uses a configured link only when it is safe: %s', (value, used) => {
    vi.stubEnv('VITE_TERMS_URL', value)
    expect(legalLinks().terms === value).toBe(used)
  })
})
