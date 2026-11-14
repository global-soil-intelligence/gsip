import { act } from '@testing-library/react'
import { StrictMode } from 'react'
import { hydrateRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { App, PAGES, RELATED_PROJECTS, STEWARDSHIP_LINE } from '../src/App'
import { headline, render } from '../src/prerender'

const roots: Root[] = []

afterEach(() => {
  for (const root of roots.splice(0)) act(() => root.unmount())
  document.body.innerHTML = ''
  vi.restoreAllMocks()
})

function structuredData(html: string) {
  const raw =
    /<script type="application\/ld\+json">([\s\S]*?)<\/script>/.exec(
      html,
    )?.[1] ?? ''
  const graph = raw
    ? (JSON.parse(raw)['@graph'] as Array<Record<string, unknown>>)
    : []
  return { graph, raw }
}

describe('prerendered pages (WP-AGENT-1)', () => {
  it('prerenders every page the build emits', () => {
    expect([...PAGES].sort()).toEqual(
      ['about', 'card', 'data', 'home', 'methods'].sort(),
    )
  })

  it.each(PAGES)('%s shows its headline without JavaScript', (page) => {
    const container = document.createElement('div')
    container.innerHTML = render(page)
    const headings = container.querySelectorAll('h1')
    expect(headings).toHaveLength(1)
    expect(headings[0]?.textContent).toBe(headline(page))
  })

  it.each(PAGES)(
    '%s describes the organization, and the dataset where it is offered',
    (page) => {
      const { graph, raw } = structuredData(render(page))
      const types = graph.map((node) => node['@type'])
      expect(types).toContain('Organization')
      expect(types).toContain(page === 'home' ? 'WebSite' : 'WebPage')
      expect(types.includes('Dataset')).toBe(page === 'home' || page === 'data')
      // The data can never close its own script element.
      expect(raw).not.toContain('<')
    },
  )

  it.each(PAGES)(
    '%s names the related open projects and its steward, and sells nothing (WP-SITE-1H)',
    (page) => {
      const container = document.createElement('div')
      container.innerHTML = render(page)
      const footer = container.querySelector('footer.site-footer')
      expect(footer).not.toBeNull()

      expect(RELATED_PROJECTS.map((project) => project.href)).toEqual([
        'https://vergecommon.com/',
        'https://dendriticforest.com/',
        'https://viridisconservation.com/ecosystem',
      ])
      for (const project of RELATED_PROJECTS) {
        const link = footer?.querySelector(`a[href="${project.href}"]`)
        expect(link?.textContent).toBe(project.name)
        const url = new URL(project.href)
        expect(url.protocol).toBe('https:')
        expect(url.search).toBe('')
        expect(url.hash).toBe('')
      }
      expect(STEWARDSHIP_LINE).toBe('GSIP is stewarded by Viridis LLC.')
      expect(footer?.textContent).toContain(STEWARDSHIP_LINE)

      // B1-B8: no price, purchase language or paid offer anywhere on the page.
      const text = container.textContent ?? ''
      expect(text).not.toMatch(
        /[$€£]\s?\d|per month|subscribe|buy now|checkout/i,
      )
      const hrefs = [...container.querySelectorAll('a[href]')].map(
        (anchor) => anchor.getAttribute('href') ?? '',
      )
      expect(
        hrefs.filter((href) =>
          /land-plans|pricing|request-access|stripe/i.test(href),
        ),
      ).toEqual([])
      // No link on the page carries tracking parameters.
      expect(hrefs.filter((href) => /[?&](utm_|ref=)/i.test(href))).toEqual([])
    },
  )

  it('licenses the dataset openly and describes estimates, not laboratory results', () => {
    const dataset = structuredData(render('data')).graph.find(
      (node) => node['@type'] === 'Dataset',
    )
    expect(dataset).toMatchObject({
      isAccessibleForFree: true,
      // Structured data and photographs carry different licences; both are declared.
      license: [
        'https://opendatacommons.org/licenses/odbl/1-0/',
        'https://creativecommons.org/licenses/by-sa/4.0/',
      ],
    })
    expect(String(dataset?.conditionsOfAccess)).toMatch(/CC BY-SA 4\.0/)
    expect(String(dataset?.description)).toMatch(/not laboratory results/)
    expect(String(dataset?.description)).toMatch(/never precise points/)
    // No download is claimed: the repository page is not a data file.
    expect(dataset).not.toHaveProperty('distribution')
  })

  it('describes a developing library without inventing spectral coverage or downloads', () => {
    const dataset = structuredData(render('data')).graph.find(
      (node) => node['@type'] === 'Dataset',
    )
    expect(dataset?.creativeWorkStatus).toBe(
      'In development; public releases gated',
    )
    expect(String(dataset?.description)).toMatch(
      /RGB images are not measured spectra/,
    )
    expect(dataset).not.toHaveProperty('spatialCoverage')
    expect(dataset).not.toHaveProperty('distribution')
    const container = document.createElement('div')
    container.innerHTML = render('home')
    expect(container.textContent).toContain(
      'Public capture and library uploads remain closed',
    )
    expect(container.querySelector('h1')?.textContent).toBe(
      'Build the world’s open soil spectral library.',
    )
  })

  it.each(PAGES)(
    '%s hydrates the prerendered markup without a mismatch',
    async (page) => {
      const container = document.createElement('div')
      container.innerHTML = render(page)
      document.body.append(container)
      const problems: unknown[] = []
      vi.spyOn(console, 'error').mockImplementation((...args) => {
        problems.push(args)
      })
      await act(async () => {
        roots.push(
          hydrateRoot(
            container,
            <StrictMode>
              <App page={page} />
            </StrictMode>,
            { onRecoverableError: (error) => problems.push(error) },
          ),
        )
      })
      expect(problems).toEqual([])
      expect(container.querySelectorAll('h1')).toHaveLength(1)
      expect(container.querySelector('h1')?.textContent).toBe(headline(page))
    },
  )
})
