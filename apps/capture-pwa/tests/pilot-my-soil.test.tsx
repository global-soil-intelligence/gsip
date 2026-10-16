import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, it } from 'vitest'
import { MySoil } from '../src/MySoilPanel'
import type { MySoilEntry } from '../src/mySoil'

afterEach(cleanup)
it.each([null, { cell: 'synthetic-coarse-cell', resolution: 8 as const }])(
  'private pilot never promises public areas, aggregation or releases',
  async (likelyPublicArea) => {
    const entry: MySoilEntry = {
      id: 'synthetic-pilot',
      capturedAt: '2026-10-16T00:00:00Z',
      status: 'passed',
      shots: { A: 'passed', B: 'passed', C: 'missing' },
      likelyPublicArea,
    }
    render(<MySoil privatePilot load={async () => [entry]} refreshKey={0} />)
    await screen.findByText('Passed the quality checks')
    expect(
      screen.getByText(/pilot observations remain private and unverified/i),
    ).toBeDefined()
    expect(document.body.textContent).not.toMatch(
      /likely public area|not public yet|3 contributors|nightly release|synthetic-coarse-cell/i,
    )
  },
)
it('requires an existing invited account instead of promising automatic account creation', async () => {
  render(<MySoil privatePilot load={async () => null} refreshKey={0} />)
  await screen.findByText(/sign in to your existing invited account/i)
  expect(document.body.textContent).not.toMatch(
    /first synced observation creates/i,
  )
})
