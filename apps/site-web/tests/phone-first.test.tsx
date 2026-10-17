import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import cardShell from '../card/index.html?raw'
import llmsBuilder from '../scripts/prerender.mjs?raw'
import { App, type PageId, pageMeta } from '../src/App'
import { render as prerender } from '../src/prerender'

afterEach(() => {
  document.body.innerHTML = ''
})

describe('phone-first public guidance', () => {
  it.each<PageId>(['home', 'card', 'methods'])(
    '%s makes the physical card optional before any collection is offered',
    (page) => {
      const { container } = render(<App page={page} />)
      expect(container.textContent).toMatch(/No printed card is needed/)
      expect(container.querySelector('a[href$="card/"]')).toBeTruthy()
      expect(
        screen.queryByRole('link', { name: /^start capture$/i }),
      ).toBeNull()
      expect(
        screen.getAllByRole('link', { name: 'Public capture closed' }).length,
      ).toBeGreaterThan(0)
      expect(prerender(page)).toMatch(/No printed card is needed/)
    },
  )

  it('starts with phone observations without claiming automatic sample registration', () => {
    const { container } = render(<App page="home" />)
    expect(container.querySelector('.steps-grid h3')?.textContent).toBe(
      'Take two phone photos',
    )
    expect(container.textContent).toMatch(
      /Library sample registration is optional/,
    )
    expect(container.textContent).toMatch(/real declared depth/)
    expect(
      container.querySelector('a[href$="gsip-reference-card-v1-color.pdf"]'),
    ).toBeTruthy()
  })

  it('keeps A and B required, C optional and both physical-card downloads reachable', () => {
    render(<App page="card" />)
    expect(
      screen.getByRole('heading', { name: 'Context · required' }),
    ).toBeTruthy()
    expect(
      screen.getByRole('heading', { name: 'Fresh face · required' }),
    ).toBeTruthy()
    expect(
      screen.getByRole('heading', { name: 'Texture · optional' }),
    ).toBeTruthy()
    expect(
      screen
        .getByRole('link', { name: 'Download color PDF' })
        .getAttribute('href'),
    ).toBe('../reference-card/gsip-reference-card-v1-color.pdf')
    expect(
      screen
        .getByRole('link', { name: 'Download B&W PDF' })
        .getAttribute('href'),
    ).toBe('../reference-card/gsip-reference-card-v1-bw.pdf')
    expect(screen.getByRole('heading', { name: 'Print at 100%' })).toBeTruthy()
  })

  it.each<PageId>(['home', 'data'])(
    '%s structured data describes the card as optional',
    (page) => {
      const { container } = render(<App page={page} />)
      const graph = JSON.parse(
        container.querySelector('script[type="application/ld+json"]')
          ?.textContent ?? '{}',
      )['@graph'] as Array<Record<string, unknown>>
      const dataset = graph.find((node) => node['@type'] === 'Dataset')
      expect(String(dataset?.measurementTechnique)).toMatch(
        /optional physical reference card/,
      )
      expect(dataset?.creativeWorkStatus).toBe(
        'In development; public releases gated',
      )
      expect(String(dataset?.description)).toMatch(
        /RGB images are not measured spectra/,
      )
    },
  )

  it('keeps card metadata and agent-facing site guidance optional and scientifically bounded', () => {
    const shell = new DOMParser().parseFromString(cardShell, 'text/html')
    for (const selector of [
      'meta[name="description"]',
      'meta[property="og:description"]',
    ]) {
      const description = shell.querySelector(selector)?.getAttribute('content')
      expect(description).toBe(pageMeta.card.description)
      expect(description).toMatch(/optional/)
    }
    expect(llmsBuilder).toMatch(/No printed card is needed/)
    expect(llmsBuilder).toMatch(/optional physical aid/)
    expect(llmsBuilder).toMatch(/ordinary photos do not automatically/i)
    expect(llmsBuilder).toMatch(
      /Public capture and library uploads remain closed/,
    )
    expect(llmsBuilder).not.toContain('print the card and follow the protocol')
  })
})
