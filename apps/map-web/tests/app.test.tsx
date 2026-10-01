import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { App } from '../src/App'

describe('map shell', () => {
  it('offers a path to contribute', () => {
    render(<App />)
    expect(screen.getByRole('link', { name: /contribute/i })).toBeDefined()
  })
})
