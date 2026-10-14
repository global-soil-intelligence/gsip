import 'fake-indexeddb/auto'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { YourData } from '../src/YourData'
import { clearQueue, enqueue, queued } from '../src/queue'
import {
  createSyncReminder,
  initialReminderState,
  type ReminderStore,
  type SyncReminderState,
} from '../src/syncReminder'
import type { ReminderNotifications } from '../src/platform/notifications'
import type { GsipClient } from '../src/supabase'
import { TERMS_VERSION } from '../src/terms'
import type { QueueRecord } from '../src/types'

const mocks = vi.hoisted(() => ({
  request: vi.fn(async (): Promise<string> => 'requested'),
}))
vi.mock('../src/supabase', () => ({
  latestDeletionRequest: async () => null,
  requestDeletion: mocks.request,
}))
beforeEach(async () => {
  await clearQueue()
  mocks.request.mockReset()
  mocks.request.mockResolvedValue('requested')
})
afterEach(() => {
  cleanup()
})
const record: QueueRecord = {
  accuracyM: null,
  attributionName: 'Synthetic contributor',
  capturedAt: '2026-10-13T00:00:00Z',
  deviceModel: 'fictional device',
  disturbed: false,
  grantId: 'fictional-grant',
  landCover: 'bare',
  latitude: 0,
  longitude: 0,
  photos: [],
  ownerUid: 'fictional-owner',
  queuedAt: '2026-10-13T00:00:00Z',
  submissionId: 'fictional-submission',
  surfaceCondition: 'dry',
  termsVersion: TERMS_VERSION,
}
function confirm(kind: 'withdrawal' | 'account deletion') {
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
}
for (const kind of ['withdrawal', 'account deletion'] as const) {
  it(`a never-settling OS schedule cannot block confirmed ${kind} or falsify its successful outcome`, async () => {
    let state = initialReminderState(),
      entered!: () => void
    const began = new Promise<void>((resolve) => {
      entered = resolve
    })
    const store: ReminderStore = {
      read: async () => ({ ...state }),
      update: async (change) => {
        state = change({ ...state })
        return { ...state }
      },
    }
    const notifications: ReminderNotifications = {
      supported: true,
      clear: async () => true,
      checkPermission: async () => 'granted',
      requestPermission: async () => 'granted',
      schedule: () => {
        entered()
        return new Promise(() => undefined)
      },
      onTap: async () => async () => undefined,
    }
    const reminder = createSyncReminder({
      notifications,
      store,
      context: async () => ({
        owner: 'fictional-owner',
        captureLive: true,
        gate: 'open',
        revision: 0,
        hasWork: true,
        blocked: false,
      }),
      focusQueue: () => undefined,
      lock: async (run) => run(),
    })
    await reminder.start()
    void reminder.enable()
    await began
    await enqueue(record)
    mocks.request.mockImplementation(async () => {
      // The rights call begins after the durable local fence, but never waits for the OS.
      expect(state.enabled).toBe(false)
      expect(state.cleanupPending).toBe(true)
      return 'requested'
    })
    const cleared = vi.fn(async () => undefined)
    render(
      <YourData
        client={{} as GsipClient}
        onBeforeRightsRequest={() => reminder.hold()}
        onQueueCleared={cleared}
      />,
    )
    confirm(kind)
    await waitFor(() => expect(mocks.request).toHaveBeenCalledTimes(1))
    expect(
      await screen.findAllByText(new RegExp(`${kind} requested on`, 'i')),
    ).toBeDefined()
    expect(screen.queryByText(/request could not be sent/i)).toBeNull()
    expect(await queued()).toEqual([])
    expect(cleared).toHaveBeenCalledTimes(1)
    expect(state.cleanupPending).toBe(true)
  })
}
it('failed server rights requests preserve queue bytes after reminder intent is fenced', async () => {
  await enqueue(record)
  mocks.request.mockRejectedValue(new Error('fictional-server-failure'))
  const fence = vi.fn(async () => undefined),
    cleared = vi.fn(async () => undefined)
  render(
    <YourData
      client={{} as GsipClient}
      onBeforeRightsRequest={fence}
      onQueueCleared={cleared}
    />,
  )
  confirm('withdrawal')
  expect(await screen.findByText(/request could not be sent/i)).toBeDefined()
  expect(fence).toHaveBeenCalledTimes(1)
  expect(await queued()).toEqual([record])
  expect(cleared).not.toHaveBeenCalled()
})
it('device reminder storage/cleanup exceptions cannot falsify a successful existing rights request', async () => {
  await enqueue(record)
  render(
    <YourData
      client={{} as GsipClient}
      onBeforeRightsRequest={async () => {
        throw new Error('fictional-private-canary')
      }}
      onQueueCleared={async () => undefined}
    />,
  )
  confirm('withdrawal')
  expect(await screen.findAllByText(/withdrawal requested on/i)).toBeDefined()
  expect(await queued()).toEqual([])
  expect(document.body.textContent).not.toContain('fictional-private-canary')
  expect(screen.queryByText(/request could not be sent/i)).toBeNull()
})

for (const kind of ['withdrawal', 'account deletion'] as const) {
  it(`a lost OS cleanup reply does not block the existing ${kind} request`, async () => {
    let state: SyncReminderState = {
        ...initialReminderState(),
        owner: 'fictional-owner',
        enabled: true,
      },
      entered!: () => void
    const began = new Promise<void>((resolve) => {
      entered = resolve
    })
    const store: ReminderStore = {
      read: async () => ({ ...state }),
      update: async (change) => {
        state = change({ ...state })
        return { ...state }
      },
    }
    const notifications: ReminderNotifications = {
      supported: true,
      clear: () => {
        entered()
        return new Promise(() => undefined)
      },
      checkPermission: async () => 'granted',
      requestPermission: async () => 'granted',
      schedule: async () => true,
      onTap: async () => async () => undefined,
    }
    const reminder = createSyncReminder({
      notifications,
      store,
      context: async () => ({
        owner: 'fictional-owner',
        captureLive: true,
        gate: 'open',
        revision: 0,
        hasWork: true,
        blocked: false,
      }),
      focusQueue: () => undefined,
      lock: async (run) => run(),
    })
    void reminder.start()
    await began
    await enqueue(record)
    mocks.request.mockImplementation(async () => {
      expect(state.enabled).toBe(false)
      expect(state.cleanupPending).toBe(true)
      return 'requested'
    })
    render(
      <YourData
        client={{} as GsipClient}
        onBeforeRightsRequest={() => reminder.hold()}
        onQueueCleared={async () => undefined}
      />,
    )
    confirm(kind)
    expect(
      await screen.findAllByText(new RegExp(`${kind} requested on`, 'i')),
    ).not.toHaveLength(0)
    expect(await queued()).toEqual([])
    expect(state.cleanupPending).toBe(true)
  })
}
