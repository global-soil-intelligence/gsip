import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { YourData } from '../src/YourData'
import type { GsipClient } from '../src/supabase'

const mocks = vi.hoisted(() => ({
  request: vi.fn(async () => 'requested'),
  clear: vi.fn(async () => 1),
}))
vi.mock('../src/supabase', async (load) => ({
  ...(await load<typeof import('../src/supabase')>()),
  requestDeletion: mocks.request,
  latestDeletionRequest: async () => null,
}))
vi.mock('../src/queue', () => ({ clearQueue: mocks.clear }))
beforeEach(() => {
  mocks.request.mockReset()
  mocks.clear.mockReset()
  mocks.clear.mockResolvedValue(1)
})
afterEach(cleanup)
function confirm(
  kind: 'withdrawal' | 'account deletion',
  cleared: () => Promise<unknown> = vi.fn(async () => undefined),
) {
  render(<YourData client={{} as GsipClient} onQueueCleared={cleared} />)
  fireEvent.click(
    screen.getByRole('button', {
      name:
        kind === 'withdrawal'
          ? /withdraw my contributions/i
          : /delete my account/i,
    }),
  )
  fireEvent.change(screen.getByLabelText(/to confirm/i), {
    target: { value: kind === 'withdrawal' ? 'WITHDRAW' : 'DELETE' },
  })
  fireEvent.click(
    screen.getByRole('button', { name: new RegExp(`confirm ${kind}`, 'i') }),
  )
  return cleared
}
it.each(['withdrawal', 'account deletion'] as const)(
  'truthfully reports the unused sign-in account for %s and preserves drafts',
  async (kind) => {
    mocks.request.mockResolvedValue('account_only')
    const cleared = confirm(kind)
    await screen.findByText(/sign-in account still exists/i)
    expect(screen.getByText(/no .*request was filed/i)).toBeDefined()
    expect(mocks.clear).not.toHaveBeenCalled()
    expect(cleared).not.toHaveBeenCalled()
    expect(screen.queryByText(/nothing.*stored on our servers/i)).toBeNull()
  },
)
for (const outcome of ['requested', 'already_open'])
  for (const phase of ['clear', 'refresh']) {
    it.each(['withdrawal', 'account deletion'] as const)(
      `${outcome} keeps confirmed server status when local ${phase} fails for %s`,
      async (kind) => {
        mocks.request.mockResolvedValue(outcome)
        const cleared = vi.fn(async () => {
          if (phase === 'refresh') throw new Error('Synthetic refresh failure')
        })
        if (phase === 'clear')
          mocks.clear.mockRejectedValue(
            new Error('Synthetic local clear failure'),
          )
        confirm(kind, cleared)
        await screen.findByText(/local cleanup is still pending/i)
        if (outcome === 'requested')
          expect(screen.getAllByText(/requested on/i).length).toBeGreaterThan(0)
        else
          expect(
            screen.getByText(/request is already in progress/i),
          ).toBeDefined()
        expect(screen.queryByText(/request could not be sent/i)).toBeNull()
      },
    )
  }
