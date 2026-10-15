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
        name: 'Build the world’s open soil spectral library.',
      }),
    ).toBeTruthy()
    expect(
      screen.getAllByRole('link', { name: 'Public capture closed' }).length,
    ).toBeGreaterThan(0)
    expect(
      screen
        .getByRole('link', { name: 'Build with GSIP' })
        .getAttribute('href'),
    ).toBe('https://github.com/global-soil-intelligence/gsip')
  })

  it('describes the dataset as unpublished when no destination is configured', () => {
    render(<App page="data" />)

    expect(
      screen.getByRole('heading', {
        level: 2,
        name: 'Public data releases remain gated.',
      }),
    ).toBeTruthy()
    expect(
      screen.queryByRole('link', { name: 'Open on Hugging Face' }),
    ).toBeNull()
  })

  it('connects builders to private local tools without offering public intake', () => {
    render(<App page="home" />)
    expect(
      screen
        .getByRole('link', { name: 'Run the synthetic library demo' })
        .getAttribute('href'),
    ).toBe(
      'https://github.com/global-soil-intelligence/gsip/blob/main/docs/SOIL_LIBRARY.md#run-the-complete-local-demo',
    )
    expect(
      screen.getByText(/Public capture and library uploads remain closed/),
    ).toBeTruthy()
    expect(screen.getByText(/private local library node/)).toBeTruthy()
    expect(screen.getByText(/same physical samples/)).toBeTruthy()
  })

  it('distinguishes phone RGB, measured spectra and unvalidated biological claims', () => {
    render(<App page="methods" />)
    expect(
      screen.getByText(/RGB images, not wavelength-resolved spectra/),
    ).toBeTruthy()
    expect(
      screen.getByText(/uncalibrated, even with the reference card/),
    ).toBeTruthy()
    expect(
      screen.getByText(/Biological relationships require actual assays/),
    ).toBeTruthy()
  })

  it('keeps photo and spectral publication gates visible', () => {
    render(<App page="data" />)
    expect(
      screen.getByText(
        /structured data only until photo screening is deployed and its calibration approved/,
      ),
    ).toBeTruthy()
    expect(
      screen.getByText(
        /Individual spectra remain private pending a fingerprinting and privacy review/,
      ),
    ).toBeTruthy()
    expect(screen.getByText(/Copies already released may persist/)).toBeTruthy()
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
