import 'fake-indexeddb/auto'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { App } from '../src/App'

describe('capture experience', () => {
  it('presents the complete privacy-safe capture protocol', async () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: /help map/i })).toBeDefined()
    expect(screen.getByText(/precise location stays private/i)).toBeDefined()
    expect(screen.getByLabelText(/A · Context/i)).toBeDefined()
    expect(screen.getByLabelText(/B · Fresh face/i)).toBeDefined()
    expect(screen.getByLabelText(/C · Moist texture/i)).toBeDefined()
    expect(document.body.textContent?.toLowerCase()).not.toContain('soil test')
  })
})
