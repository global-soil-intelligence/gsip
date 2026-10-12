import 'fake-indexeddb/auto'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { App } from '../src/App'

afterEach(() => {
  cleanup()
  vi.unstubAllEnvs()
})

describe('capture experience', () => {
  it('presents the complete privacy-safe capture protocol when capture is live', async () => {
    vi.stubEnv('VITE_CAPTURE_LIVE', 'true')
    render(<App />)
    expect(screen.getByRole('heading', { name: /help map/i })).toBeDefined()
    expect(screen.getByText(/precise location stays private/i)).toBeDefined()
    expect(screen.getByLabelText(/A · Context/i)).toBeDefined()
    expect(screen.getByLabelText(/B · Fresh face/i)).toBeDefined()
    expect(screen.getByLabelText(/C · Moist texture/i)).toBeDefined()
    expect(screen.getByText(/two photos\. one card/i)).toBeDefined()
    expect(document.body.textContent?.toLowerCase()).not.toContain('soil test')
    expect(document.body.textContent?.toLowerCase()).not.toContain('history')
  })

  it('stays closed unless the build opens capture', () => {
    render(<App />)
    expect(
      screen.getByRole('heading', {
        name: /contributions open after our launch review/i,
      }),
    ).toBeDefined()
    expect(screen.queryByLabelText(/B · Fresh face/i)).toBeNull()
    expect(
      screen.queryByRole('button', { name: /queue observation/i }),
    ).toBeNull()
  })

  it('warns that a typed attribution name is published with the area and date', () => {
    vi.stubEnv('VITE_CAPTURE_LIVE', 'true')
    render(<App />)
    const field = screen.getByLabelText(/public photo attribution/i)
    expect(field.getAttribute('aria-describedby')).toBe('attribution-hint')
    expect(
      screen.getByText(/published with your photo’s area and date/i),
    ).toBeDefined()
  })

  it('refuses an attribution name the database would reject', async () => {
    vi.stubEnv('VITE_CAPTURE_LIVE', 'true')
    render(<App />)
    const jpeg = new File(['jpeg'], 'soil.jpg', { type: 'image/jpeg' })
    fireEvent.change(screen.getByLabelText(/A · Context/i), {
      target: { files: [jpeg] },
    })
    fireEvent.change(screen.getByLabelText(/B · Fresh face/i), {
      target: { files: [jpeg] },
    })
    fireEvent.change(screen.getByLabelText('Latitude'), {
      target: { value: '44.4759' },
    })
    fireEvent.change(screen.getByLabelText('Longitude'), {
      target: { value: '-73.2121' },
    })
    fireEvent.change(screen.getByLabelText(/public photo attribution/i), {
      target: { value: 'visit https://spam.example' },
    })
    fireEvent.submit(
      screen
        .getByRole('button', { name: /queue observation/i })
        .closest('form')!,
    )
    expect(
      await screen.findByText(/check the public attribution name/i),
    ).toBeDefined()
    expect(
      screen
        .getByLabelText(/public photo attribution/i)
        .getAttribute('aria-invalid'),
    ).toBe('true')
    expect(screen.queryByText(/1 queued/i)).toBeNull()
  })
})
