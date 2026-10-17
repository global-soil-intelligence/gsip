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
    expect(
      screen.getByText(/two required photos\. one optional/i),
    ).toBeDefined()
    expect(
      screen.getByRole('heading', {
        name: 'Ready for your first observation.',
      }),
    ).toBeDefined()
    expect(
      screen.queryByRole('heading', { name: 'Collection is closed.' }),
    ).toBeNull()
    expect(document.body.textContent?.toLowerCase()).not.toContain('soil test')
    expect(document.body.textContent?.toLowerCase()).not.toContain('history')
  })

  it('explains card-free capture before the form and keeps optional physical help reachable', () => {
    vi.stubEnv('VITE_CAPTURE_LIVE', 'true')
    render(<App />)
    const guidance = screen.getByText('No printed card needed.')
    const form = screen
      .getByRole('button', { name: /queue observation/i })
      .closest('form')!
    expect(
      guidance.compareDocumentPosition(form) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).not.toBe(0)
    expect(
      screen
        .getByRole('link', { name: /optional printable A6 card/i })
        .getAttribute('href'),
    ).toMatch(/reference-card\/gsip-reference-card-v1-color\.pdf$/)
    const help = screen
      .getByText('Optional physical reference card')
      .closest('details')!
    expect(help).not.toBeNull()
    expect(help.open).toBe(false)
    fireEvent.click(screen.getByText('Optional physical reference card'))
    expect(help.open).toBe(true)
    expect(help.textContent).toMatch(/not a certified reflectance target/i)
    expect(screen.getAllByText('Frame the soil for this shot')).toHaveLength(3)
    expect(screen.queryByText(/keep card \+ soil/i)).toBeNull()
    expect(document.querySelector('video')).toBeNull()
    expect(
      (screen.getByLabelText(/A · Context/i) as HTMLInputElement).required,
    ).toBe(true)
    expect(
      (screen.getByLabelText(/B · Fresh face/i) as HTMLInputElement).required,
    ).toBe(true)
    expect(
      (screen.getByLabelText(/C · Moist texture/i) as HTMLInputElement)
        .required,
    ).toBe(false)
  })

  it.each([undefined, 'false'])(
    'reports collection closed without upload controls for capture flag %s',
    (captureFlag) => {
      vi.stubEnv('VITE_CAPTURE_LIVE', captureFlag)
      render(<App />)
      expect(
        screen.getByRole('heading', { name: 'Collection is not open yet.' }),
      ).toBeDefined()
      expect(
        screen.getByRole('heading', { name: 'Collection is closed.' }),
      ).toBeDefined()
      expect(
        screen.queryByRole('heading', {
          name: 'Ready for your first observation.',
        }),
      ).toBeNull()
      expect(document.body.textContent).not.toMatch(/privacy and legal review/i)
      expect(screen.queryByLabelText(/A · Context/i)).toBeNull()
      expect(screen.queryByLabelText(/B · Fresh face/i)).toBeNull()
      expect(screen.queryByLabelText(/C · Moist texture/i)).toBeNull()
      expect(
        screen.queryByRole('button', { name: /queue observation/i }),
      ).toBeNull()
      expect(
        screen.getByRole('link', { name: /explore the map/i }),
      ).toBeDefined()
    },
  )

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
