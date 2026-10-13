import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { App, type PageId } from '../src/App'

afterEach(() => {
  document.body.innerHTML = ''
})

describe('public website', () => {
  it.each<PageId>(['home', 'card', 'methods', 'data', 'about'])(
    'renders exactly one primary heading on %s',
    (page) => {
      const { container } = render(<App page={page} />)
      expect(container.querySelectorAll('h1')).toHaveLength(1)
    },
  )

  it('keeps capture visibly closed by default', () => {
    render(<App page="home" />)

    expect(
      screen.getByRole('heading', {
        level: 1,
        name: 'Build the world’s living soil map.',
      }),
    ).toBeTruthy()
    expect(
      screen.getAllByRole('link', { name: 'Capture opening soon' }).length,
    ).toBeGreaterThan(0)
    expect(
      screen
        .getByRole('link', { name: 'Explore the map' })
        .getAttribute('href'),
    ).toBe('./map/')
  })

  it('describes the dataset as unpublished when no destination is configured', () => {
    render(<App page="data" />)

    expect(
      screen.getByRole('heading', {
        level: 2,
        name: 'The export is built. The public repository is not live yet.',
      }),
    ).toBeTruthy()
    expect(
      screen.queryByRole('link', { name: 'Open on Hugging Face' }),
    ).toBeNull()
  })

  it('states the public and private location boundary', () => {
    render(<App page="methods" />)

    expect(
      screen.getByRole('heading', {
        name: 'Every public cell holds at least three contributors.',
      }),
    ).toBeTruthy()
    expect(
      screen.getByText(/Exact geometry remains protected operational data/),
    ).toBeTruthy()
  })

  it('points agents to the guide, and to no interface until one is configured', () => {
    render(<App page="data" />)

    expect(
      screen.getByRole('link', { name: 'Agent guide' }).getAttribute('href'),
    ).toBe(
      'https://github.com/global-soil-intelligence/gsip/blob/main/docs/AGENTS.md',
    )
    expect(
      screen.queryByRole('link', { name: 'OpenAPI description' }),
    ).toBeNull()
    expect(screen.queryByText(/MCP endpoint/)).toBeNull()
  })
})

describe('public website with the read API deployed', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.resetModules()
  })

  it('links the OpenAPI description and names the MCP endpoint', async () => {
    vi.stubEnv(
      'VITE_GSIP_PUBLIC_API',
      ' https://project.supabase.co/functions/v1/gsip-public/ ',
    )
    vi.resetModules()
    const { App: Configured } = await import('../src/App')
    render(<Configured page="data" />)

    expect(
      screen
        .getByRole('link', { name: 'OpenAPI description' })
        .getAttribute('href'),
    ).toBe(
      'https://project.supabase.co/functions/v1/gsip-public/v1/openapi.json',
    )
    expect(
      screen.getByText(
        'https://project.supabase.co/functions/v1/gsip-public/mcp',
      ).tagName,
    ).toBe('CODE')
  })

  it('names the published dataset as the same thing, without claiming a download', async () => {
    const hub = 'https://huggingface.co/datasets/global-soil-intelligence/gsip'
    vi.stubEnv('VITE_DATASET_URL', hub)
    vi.resetModules()
    const { App: Configured } = await import('../src/App')
    const { container } = render(<Configured page="data" />)

    const graph = JSON.parse(
      container.querySelector('script[type="application/ld+json"]')
        ?.textContent ?? '{}',
    )['@graph'] as Array<Record<string, unknown>>
    const dataset = graph.find((node) => node['@type'] === 'Dataset')
    expect(dataset?.sameAs).toBe(hub)
    expect(dataset).not.toHaveProperty('distribution')
  })
})
