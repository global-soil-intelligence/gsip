import { act } from '@testing-library/react'
import { StrictMode } from 'react'
import { hydrateRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { App, PAGES } from '../src/App'
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

  it('licenses the dataset openly and describes estimates, not laboratory results', () => {
    const dataset = structuredData(render('data')).graph.find(
      (node) => node['@type'] === 'Dataset',
    )
    expect(dataset).toMatchObject({
      isAccessibleForFree: true,
      license: 'https://opendatacommons.org/licenses/odbl/1-0/',
    })
    expect(String(dataset?.description)).toMatch(/not laboratory results/)
    expect(String(dataset?.description)).toMatch(/never precise points/)
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
