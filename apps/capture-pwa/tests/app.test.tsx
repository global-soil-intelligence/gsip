import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { App } from '../src/App'

describe('capture shell', () => {
  it('describes the pending capture flow without calling it a test', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: /soil capture/i })).toBeDefined()
    expect(document.body.textContent?.toLowerCase()).not.toContain('soil test')
  })
})
