import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

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
        name: 'H3 resolution 8 is the public location boundary.',
      }),
    ).toBeTruthy()
    expect(
      screen.getByText(/Exact geometry remains protected operational data/),
    ).toBeTruthy()
  })
})
