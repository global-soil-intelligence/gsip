import { expect, it, vi } from 'vitest'
import {
  createSyncReminder,
  initialReminderState,
  REMINDER_DELAY,
  type ReminderContext,
  type ReminderStore,
} from '../src/syncReminder'
import {
  selectReminderNotifications,
  SYNC_REMINDER_ID,
  type ReminderNotifications,
  type ReminderPermission,
} from '../src/platform/notifications'
import type { LocalNotificationsPlugin } from '@capacitor/local-notifications'

const deferred = <T>() => {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => {
    resolve = done
  })
  return { promise, resolve }
}
function fixture() {
  let state = initialReminderState()
  let tail: Promise<unknown> = Promise.resolve()
  const store: ReminderStore = {
    read: async () => structuredClone(state),
    update(change) {
      const next = tail.then(() => {
        state = structuredClone(change(structuredClone(state)))
        return structuredClone(state)
      })
      tail = next
      return next
    },
  }
  let current: ReminderContext = {
    owner: 'fictional-owner',
    captureLive: true,
    gate: 'open',
    revision: 0,
    hasWork: true,
    blocked: false,
  }
  const notifications: ReminderNotifications = {
    supported: true,
    checkPermission: vi.fn(async (): Promise<ReminderPermission> => 'granted'),
    requestPermission: vi.fn(
      async (): Promise<ReminderPermission> => 'granted',
    ),
    schedule: vi.fn(async () => true),
    clear: vi.fn(async () => true),
    onTap: vi.fn(async () => async () => undefined),
  }
  const focusQueue = vi.fn()
  const changed = vi.fn()
  let lockTail: Promise<unknown> = Promise.resolve()
  const lock = <T>(run: () => Promise<T>): Promise<T> => {
    const next = lockTail.then(run)
    lockTail = next
    return next
  }
  const make = (provider = notifications) =>
    createSyncReminder({
      notifications: provider,
      store,
      context: async () => ({ ...current }),
      focusQueue,
      changed,
      lock,
      now: () => 1_800_000_000_000,
    })
  return {
    make,
    store,
    notifications,
    focusQueue,
    changed,
    get state() {
      return state
    },
    updateContext(change: Partial<ReminderContext>) {
      current = { ...current, ...change }
    },
  }
}

it('startup clears owned state but never asks permission or schedules without opt-in', async () => {
  const f = fixture(),
    reminder = f.make()
  await reminder.start()
  expect(f.notifications.clear).toHaveBeenCalled()
  expect(f.notifications.requestPermission).not.toHaveBeenCalled()
  expect(f.notifications.schedule).not.toHaveBeenCalled()
  expect(f.state.enabled).toBe(false)
})
it('explicit opt-in schedules once after one day and refresh/partial sync never re-arms', async () => {
  const f = fixture(),
    reminder = f.make()
  await reminder.start()
  await reminder.enable()
  expect(f.notifications.requestPermission).toHaveBeenCalledTimes(1)
  expect(f.notifications.schedule).toHaveBeenCalledExactlyOnceWith(
    1_800_000_000_000 + REMINDER_DELAY,
    expect.objectContaining({
      fresh: expect.any(Function),
      local: expect.any(Function),
    }),
  )
  await Promise.all([
    reminder.refresh(),
    reminder.refresh(),
    reminder.refresh(),
  ])
  await reminder.synced()
  expect(f.notifications.schedule).toHaveBeenCalledTimes(1)
  expect(f.state.consumed).toBe(true)
  f.updateContext({ hasWork: false })
  await reminder.refresh()
  f.updateContext({ hasWork: true })
  await reminder.refresh()
  expect(f.notifications.schedule).toHaveBeenCalledTimes(2)
})
it('restart cleans native state and preserves consumed-cycle intent without another reminder', async () => {
  const f = fixture(),
    first = f.make()
  await first.start()
  await first.enable()
  await first.stop()
  await first.settled()
  const second = f.make()
  await second.start()
  await second.refresh()
  expect(f.state.enabled).toBe(true)
  expect(f.notifications.schedule).toHaveBeenCalledTimes(1)
})
for (const permission of ['denied', 'unknown'] as const) {
  it(`explicit ${permission} permission response leaves capture usable and never schedules`, async () => {
    const f = fixture(),
      reminder = f.make()
    vi.mocked(f.notifications.requestPermission).mockResolvedValue(permission)
    await reminder.start()
    await reminder.enable()
    await reminder.refresh()
    expect(f.state.enabled).toBe(false)
    expect(f.notifications.schedule).not.toHaveBeenCalled()
    expect(f.notifications.requestPermission).toHaveBeenCalledTimes(1)
  })
}
for (const change of [
  { owner: null },
  { owner: 'different-fictional-owner' },
  { gate: 'closed' },
  { gate: 'unknown' },
  { captureLive: false },
  { hasWork: false },
  { blocked: true },
  { revision: 1 },
] satisfies Partial<ReminderContext>[]) {
  it(`invalidates and clears after the context transition ${JSON.stringify(change)}`, async () => {
    const f = fixture(),
      reminder = f.make()
    await reminder.start()
    await reminder.enable()
    const clears = vi.mocked(f.notifications.clear).mock.calls.length
    f.updateContext(change)
    await reminder.refresh()
    expect(vi.mocked(f.notifications.clear).mock.calls.length).toBeGreaterThan(
      clears,
    )
    expect(f.notifications.schedule).toHaveBeenCalledTimes(1)
  })
}
it('known closed/unknown/foreign/held queues cannot ask permission even on an opt-in click', async () => {
  for (const change of [
    { gate: 'closed' },
    { gate: 'unknown' },
    { owner: null },
    { blocked: true },
  ] satisfies Partial<ReminderContext>[]) {
    const f = fixture()
    f.updateContext(change)
    const reminder = f.make()
    await reminder.start()
    await reminder.enable()
    expect(f.notifications.requestPermission).not.toHaveBeenCalled()
    expect(f.notifications.schedule).not.toHaveBeenCalled()
  }
})
it('settings permission revocation cancels the one-shot without requesting permission again', async () => {
  const f = fixture(),
    reminder = f.make()
  await reminder.start()
  await reminder.enable()
  const clears = vi.mocked(f.notifications.clear).mock.calls.length
  vi.mocked(f.notifications.checkPermission).mockResolvedValue('denied')
  await reminder.refresh()
  expect(vi.mocked(f.notifications.clear).mock.calls.length).toBeGreaterThan(
    clears,
  )
  expect(f.notifications.requestPermission).toHaveBeenCalledTimes(1)
  expect(f.notifications.schedule).toHaveBeenCalledTimes(1)
})
for (const invalidate of ['disable', 'hold', 'stop'] as const) {
  it(`a late permission grant after ${invalidate} cannot re-enable intent`, async () => {
    const f = fixture(),
      reminder = f.make(),
      pending = deferred<ReminderPermission>()
    const entered = deferred<void>()
    vi.mocked(f.notifications.requestPermission).mockImplementation(() => {
      entered.resolve()
      return pending.promise
    })
    await reminder.start()
    const enabling = reminder.enable()
    await entered.promise
    await reminder[invalidate]()
    pending.resolve('granted')
    await enabling
    await reminder.settled()
    expect(f.state.enabled).toBe(false)
    expect(f.notifications.schedule).not.toHaveBeenCalled()
  })
}
it('a late schedule completes before cleanup, so an earlier cancellation cannot be the sole proof', async () => {
  const f = fixture(),
    reminder = f.make(),
    pending = deferred<boolean>(),
    entered = deferred<void>()
  const order: string[] = []
  vi.mocked(f.notifications.schedule).mockImplementation(async () => {
    entered.resolve()
    await pending.promise
    order.push('schedule-finished')
    return true
  })
  vi.mocked(f.notifications.clear).mockImplementation(async () => {
    order.push('clear')
    return true
  })
  await reminder.start()
  const enabling = reminder.enable()
  await entered.promise
  await reminder.disable()
  expect(f.state.cleanupPending).toBe(true)
  pending.resolve(true)
  await enabling
  await reminder.settled()
  expect(order.slice(order.indexOf('schedule-finished') + 1)).toContain('clear')
  expect(f.state.enabled).toBe(false)
  expect(f.state.cleanupPending).toBe(false)
})
it('a schedule reply that never settles does not block the durable rights fence', async () => {
  const f = fixture(),
    reminder = f.make(),
    entered = deferred<void>()
  vi.mocked(f.notifications.schedule).mockImplementation(() => {
    entered.resolve()
    return new Promise(() => undefined)
  })
  await reminder.start()
  void reminder.enable()
  await entered.promise
  await reminder.hold()
  const request = vi.fn(async () => 'requested')
  expect(await request()).toBe('requested')
  expect(f.state.enabled).toBe(false)
  expect(f.state.cleanupPending).toBe(true)
})
it('unknown cleanup/readback prevents scheduling until actual absence is verified', async () => {
  const f = fixture(),
    reminder = f.make()
  vi.mocked(f.notifications.clear).mockResolvedValue(false)
  await reminder.start()
  await reminder.enable()
  await reminder.refresh()
  expect(f.state.cleanupPending).toBe(true)
  expect(f.notifications.schedule).not.toHaveBeenCalled()
  vi.mocked(f.notifications.clear).mockResolvedValue(true)
  await reminder.refresh()
  await reminder.enable()
  expect(f.notifications.schedule).toHaveBeenCalledTimes(1)
})
it('a lost schedule outcome consumes the cycle and remains conservative on restart', async () => {
  const f = fixture(),
    first = f.make()
  vi.mocked(f.notifications.schedule).mockResolvedValue(false)
  await first.start()
  await first.enable()
  await first.stop()
  await first.settled()
  const second = f.make()
  await second.start()
  await second.refresh()
  expect(f.state.consumed).toBe(true)
  expect(f.notifications.schedule).toHaveBeenCalledTimes(1)
})
it('overlapping coordinators atomically share one cycle and native operations', async () => {
  const f = fixture(),
    first = f.make(),
    second = f.make()
  await Promise.all([first.start(), second.start()])
  await first.enable()
  await Promise.all([
    first.refresh(),
    second.refresh(),
    first.refresh(),
    second.refresh(),
  ])
  expect(f.notifications.schedule).toHaveBeenCalledTimes(1)
})
it('tap checks fresh local ownership/gate/permission and disposal prevents stale callbacks', async () => {
  const f = fixture(),
    reminder = f.make()
  let tap: () => void = () => undefined
  const remove = vi.fn(async () => undefined)
  vi.mocked(f.notifications.onTap).mockImplementation(async (callback) => {
    tap = callback
    return remove
  })
  await reminder.start()
  await reminder.enable()
  tap()
  await reminder.settled()
  expect(f.focusQueue).toHaveBeenCalledTimes(1)
  f.updateContext({ gate: 'closed' })
  tap()
  await reminder.settled()
  expect(f.focusQueue).toHaveBeenCalledTimes(1)
  await reminder.stop()
  await reminder.settled()
  tap()
  await reminder.settled()
  expect(remove).toHaveBeenCalledTimes(1)
  expect(f.focusQueue).toHaveBeenCalledTimes(1)
})
it('unknown thrown context/native details remain generic and never logged', async () => {
  const f = fixture(),
    changed = vi.fn(),
    log = vi.spyOn(console, 'error')
  const reminder = createSyncReminder({
    notifications: f.notifications,
    store: f.store,
    context: async () => {
      throw new Error('fictional-private-canary')
    },
    focusQueue: f.focusQueue,
    changed,
    lock: async (run) => run(),
  })
  await reminder.start()
  await reminder.enable()
  expect(JSON.stringify(changed.mock.calls)).not.toContain(
    'fictional-private-canary',
  )
  expect(log).not.toHaveBeenCalled()
  log.mockRestore()
})
it('unsupported cross-context locks hold scheduling and still attempt owned cleanup', async () => {
  const f = fixture(),
    reminder = createSyncReminder({
      notifications: f.notifications,
      store: f.store,
      context: async () => ({
        owner: 'fictional-owner',
        captureLive: true,
        gate: 'open',
        revision: 0,
        hasWork: true,
        blocked: false,
      }),
      focusQueue: f.focusQueue,
      lock: async () => undefined,
    })
  await reminder.start()
  await reminder.enable()
  expect(f.notifications.clear).toHaveBeenCalled()
  expect(f.notifications.requestPermission).not.toHaveBeenCalled()
  expect(f.notifications.schedule).not.toHaveBeenCalled()
})

it('a listener registration arriving after stop removes its handle and ignores stale callbacks without storage writes', async () => {
  const f = fixture(),
    entered = deferred<void>(),
    registration = deferred<() => Promise<void>>()
  const remove = vi.fn(async () => undefined),
    writes = vi.spyOn(f.store, 'update')
  let tap: () => void = () => undefined
  vi.mocked(f.notifications.onTap).mockImplementation((callback) => {
    tap = callback
    entered.resolve()
    return registration.promise
  })
  const reminder = f.make(),
    starting = reminder.start()
  await entered.promise
  await reminder.stop()
  registration.resolve(remove)
  await starting
  await reminder.settled()
  expect(remove).toHaveBeenCalledTimes(1)
  const before = writes.mock.calls.length
  tap()
  await reminder.settled()
  expect(writes).toHaveBeenCalledTimes(before)
  expect(f.focusQueue).not.toHaveBeenCalled()
})
it('a durable hold in another coordinator during actual adapter await prevents SDK schedule dispatch', async () => {
  const f = fixture()
  const plugin = {
    checkPermissions: vi.fn(async () => ({ display: 'granted' })),
    requestPermissions: vi.fn(async () => ({ display: 'granted' })),
    schedule: vi.fn(async () => ({
      notifications: [{ id: SYNC_REMINDER_ID }],
    })),
    cancel: vi.fn(async () => undefined),
    removeDeliveredNotificationsById: vi.fn(async () => undefined),
    getPending: vi.fn(async () => ({ notifications: [] })),
    getDeliveredNotifications: vi.fn(async () => ({ notifications: [] })),
    addListener: vi.fn(async () => ({ remove: async () => undefined })),
  }
  const actual = selectReminderNotifications(true, async () => ({
    api: plugin as unknown as LocalNotificationsPlugin,
  }))
  const peer = f.make(actual)
  let held: Promise<void> | undefined
  const provider: ReminderNotifications = {
    ...actual,
    schedule(at, intent) {
      const pending = actual.schedule(at, intent)
      // The cached plugin Promise yields, so the peer's durable hold precedes actual SDK dispatch.
      held = peer.hold()
      return pending
    },
  }
  const original = f.make(provider)
  await original.start()
  await original.enable()
  await held
  await original.settled()
  await peer.settled()
  expect(f.state.enabled).toBe(false)
  expect(plugin.schedule).not.toHaveBeenCalled()
})
it('a durable peer hold during actual adapter permission await cannot dispatch a native prompt', async () => {
  const f = fixture()
  const plugin = {
    checkPermissions: vi.fn(async () => ({ display: 'granted' })),
    requestPermissions: vi.fn(async () => ({ display: 'granted' })),
    schedule: vi.fn(async () => ({
      notifications: [{ id: SYNC_REMINDER_ID }],
    })),
    cancel: vi.fn(async () => undefined),
    removeDeliveredNotificationsById: vi.fn(async () => undefined),
    getPending: vi.fn(async () => ({ notifications: [] })),
    getDeliveredNotifications: vi.fn(async () => ({ notifications: [] })),
    addListener: vi.fn(async () => ({ remove: async () => undefined })),
  }
  const actual = selectReminderNotifications(true, async () => ({
    api: plugin as unknown as LocalNotificationsPlugin,
  }))
  const peer = f.make(actual)
  let held: Promise<void> | undefined
  const provider: ReminderNotifications = {
    ...actual,
    requestPermission(intent) {
      const pending = actual.requestPermission(intent)
      held = peer.hold()
      return pending
    },
  }
  const original = f.make(provider)
  await original.start()
  await original.enable()
  await held
  await original.settled()
  await peer.settled()
  expect(f.state.enabled).toBe(false)
  expect(plugin.requestPermissions).not.toHaveBeenCalled()
  expect(plugin.schedule).not.toHaveBeenCalled()
})
for (const transition of [
  { gate: 'closed' },
  { owner: 'different-fictional-owner' },
  { revision: 1 },
  { blocked: true },
] satisfies Partial<ReminderContext>[]) {
  it(`fresh context after the actual adapter await fences ${JSON.stringify(transition)} before SDK scheduling`, async () => {
    const f = fixture()
    const plugin = {
      checkPermissions: vi.fn(async () => ({ display: 'granted' })),
      requestPermissions: vi.fn(async () => ({ display: 'granted' })),
      schedule: vi.fn(async () => ({
        notifications: [{ id: SYNC_REMINDER_ID }],
      })),
      cancel: vi.fn(async () => undefined),
      removeDeliveredNotificationsById: vi.fn(async () => undefined),
      getPending: vi.fn(async () => ({ notifications: [] })),
      getDeliveredNotifications: vi.fn(async () => ({ notifications: [] })),
      addListener: vi.fn(async () => ({ remove: async () => undefined })),
    }
    const actual = selectReminderNotifications(true, async () => ({
      api: plugin as unknown as LocalNotificationsPlugin,
    }))
    const provider: ReminderNotifications = {
      ...actual,
      schedule(at, intent) {
        const pending = actual.schedule(at, intent)
        f.updateContext(transition)
        return pending
      },
    }
    const reminder = f.make(provider)
    await reminder.start()
    await reminder.enable()
    await reminder.settled()
    expect(plugin.schedule).not.toHaveBeenCalled()
  })
}
it('repeated start removes an old lifecycle listener and keeps only the current callback usable', async () => {
  const f = fixture(),
    taps: (() => void)[] = [],
    removals: ReturnType<typeof vi.fn>[] = []
  vi.mocked(f.notifications.onTap).mockImplementation(async (callback) => {
    taps.push(callback)
    const remove = vi.fn(async () => undefined)
    removals.push(remove)
    return remove
  })
  const reminder = f.make()
  await reminder.start()
  await reminder.enable()
  await reminder.start()
  expect(removals[0]).toHaveBeenCalledTimes(1)
  const writes = vi.spyOn(f.store, 'update')
  taps[0]()
  await reminder.settled()
  expect(writes).not.toHaveBeenCalled()
  taps[1]()
  await reminder.settled()
  expect(f.focusQueue).toHaveBeenCalledTimes(1)
  await reminder.stop()
  await reminder.settled()
  expect(removals[1]).toHaveBeenCalledTimes(1)
})
it('disposed coordinator actions cannot overwrite or clear a replacement owner', async () => {
  const f = fixture()
  const oldContext: ReminderContext = {
    owner: 'old-fictional-owner',
    captureLive: true,
    gate: 'open',
    revision: 0,
    hasWork: true,
    blocked: false,
  }
  const nextContext = {
    ...oldContext,
    owner: 'new-fictional-owner',
    revision: 1,
  }
  const make = (context: ReminderContext) =>
    createSyncReminder({
      notifications: f.notifications,
      store: f.store,
      context: async () => ({ ...context }),
      focusQueue: f.focusQueue,
      lock: async (run) => run(),
    })
  const old = make(oldContext)
  await old.start()
  await old.enable()
  await old.stop()
  await old.settled()
  const replacement = make(nextContext)
  await replacement.start()
  await replacement.enable()
  await replacement.settled()
  const before = structuredClone(f.state),
    clears = vi.mocked(f.notifications.clear).mock.calls.length
  const reads = vi.spyOn(f.store, 'read'),
    writes = vi.spyOn(f.store, 'update')
  for (const action of [
    'refresh',
    'enable',
    'disable',
    'hold',
    'gatesChanged',
    'synced',
    'stop',
  ] as const)
    await old[action]()
  await old.settled()
  expect(f.state).toEqual(before)
  expect(f.notifications.clear).toHaveBeenCalledTimes(clears)
  expect(reads).not.toHaveBeenCalled()
  expect(writes).not.toHaveBeenCalled()
})
it('a context await begun before stop cannot observe or commit the old owner after replacement', async () => {
  const f = fixture(),
    entered = deferred<void>(),
    result = deferred<ReminderContext>()
  const oldContext: ReminderContext = {
    owner: 'old-fictional-owner',
    captureLive: true,
    gate: 'open',
    revision: 0,
    hasWork: true,
    blocked: false,
  }
  let delayed = false
  const old = createSyncReminder({
    notifications: f.notifications,
    store: f.store,
    context: async () => {
      if (delayed) {
        entered.resolve()
        return result.promise
      }
      return { ...oldContext }
    },
    focusQueue: f.focusQueue,
    lock: async (run) => run(),
  })
  await old.start()
  await old.enable()
  delayed = true
  const refreshing = old.refresh()
  await entered.promise
  await old.stop()
  const replacement = createSyncReminder({
    notifications: f.notifications,
    store: f.store,
    context: async () => ({
      ...oldContext,
      owner: 'new-fictional-owner',
      revision: 1,
    }),
    focusQueue: f.focusQueue,
    lock: async (run) => run(),
  })
  await replacement.start()
  await replacement.enable()
  await replacement.settled()
  const before = structuredClone(f.state),
    clears = vi.mocked(f.notifications.clear).mock.calls.length
  result.resolve(oldContext)
  await refreshing
  await old.settled()
  expect(f.state).toEqual(before)
  expect(f.notifications.clear).toHaveBeenCalledTimes(clears)
})
it('an old refresh queued at the lock boundary cannot execute after disposal and replacement', async () => {
  const f = fixture(),
    entered = deferred<void>(),
    released = deferred<void>()
  const oldContext: ReminderContext = {
    owner: 'old-fictional-owner',
    captureLive: true,
    gate: 'open',
    revision: 0,
    hasWork: true,
    blocked: false,
  }
  let delayNext = false
  const old = createSyncReminder({
    notifications: f.notifications,
    store: f.store,
    context: async () => ({ ...oldContext }),
    focusQueue: f.focusQueue,
    lock: async (run) => {
      if (delayNext) {
        delayNext = false
        entered.resolve()
        await released.promise
      }
      return run()
    },
  })
  await old.start()
  await old.enable()
  delayNext = true
  const refreshing = old.refresh()
  await entered.promise
  await old.stop()
  const replacement = createSyncReminder({
    notifications: f.notifications,
    store: f.store,
    context: async () => ({
      ...oldContext,
      owner: 'new-fictional-owner',
      revision: 1,
    }),
    focusQueue: f.focusQueue,
    lock: async (run) => run(),
  })
  await replacement.start()
  await replacement.enable()
  await replacement.settled()
  const before = structuredClone(f.state),
    clears = vi.mocked(f.notifications.clear).mock.calls.length
  released.resolve()
  await refreshing
  await old.settled()
  expect(f.state).toEqual(before)
  expect(f.notifications.clear).toHaveBeenCalledTimes(clears)
})
it('an admitted update that resumes before committing cannot overwrite a replacement lifetime', async () => {
  const f = fixture(),
    entered = deferred<void>(),
    released = deferred<void>()
  const originalUpdate = f.store.update
  let delayNext = false
  f.store.update = async (change) => {
    if (delayNext) {
      delayNext = false
      entered.resolve()
      await released.promise
    }
    return originalUpdate(change)
  }
  const oldContext: ReminderContext = {
    owner: 'old-fictional-owner',
    captureLive: true,
    gate: 'open',
    revision: 0,
    hasWork: true,
    blocked: false,
  }
  const old = createSyncReminder({
    notifications: f.notifications,
    store: f.store,
    context: async () => ({ ...oldContext }),
    focusQueue: f.focusQueue,
    lock: async (run) => run(),
  })
  await old.start()
  await old.enable()
  delayNext = true
  const refreshing = old.refresh()
  await entered.promise
  await old.stop()
  const replacement = createSyncReminder({
    notifications: f.notifications,
    store: f.store,
    context: async () => ({
      ...oldContext,
      owner: 'new-fictional-owner',
      revision: 1,
    }),
    focusQueue: f.focusQueue,
    lock: async (run) => run(),
  })
  await replacement.start()
  await replacement.enable()
  await replacement.settled()
  const before = structuredClone(f.state),
    clears = vi.mocked(f.notifications.clear).mock.calls.length
  released.resolve()
  await refreshing
  await old.settled()
  expect(f.state).toEqual(before)
  expect(f.notifications.clear).toHaveBeenCalledTimes(clears)
})

for (const stopTurn of [undefined, -1, 1, 2]) {
  it(`the final tap focus belongs only to its active lifecycle at stop turn ${stopTurn ?? 'active'}`, async () => {
    let state = initialReminderState(),
      monitor = false,
      observations = 0,
      queuedStop = false,
      disposed = false,
      tap: () => void = () => undefined
    const focusedWhileDisposed: boolean[] = []
    const store: ReminderStore = {
      read: async () => structuredClone(state),
      update: async (change) => {
        state = structuredClone(change(structuredClone(state)))
        const result = structuredClone(state)
        if (
          monitor &&
          observations === 2 &&
          !queuedStop &&
          stopTurn !== undefined &&
          stopTurn >= 0
        ) {
          queuedStop = true
          let turn: Promise<unknown> = Promise.resolve()
          for (let index = 0; index < stopTurn; index += 1)
            turn = turn.then(() => undefined)
          void turn.then(() => {
            disposed = true
            void reminder.stop()
          })
        }
        return result
      },
    }
    const notifications = fixture().notifications
    vi.mocked(notifications.onTap).mockImplementation(async (callback) => {
      tap = callback
      return async () => undefined
    })
    const reminder = createSyncReminder({
      store,
      notifications,
      context: async () => {
        if (monitor) observations += 1
        return {
          owner: 'fictional-tap-owner',
          captureLive: true,
          gate: 'open',
          revision: 0,
          hasWork: true,
          blocked: false,
        }
      },
      lock: async (run) => run(),
      focusQueue: () => focusedWhileDisposed.push(disposed),
      changed: () => undefined,
    })
    await reminder.start()
    await reminder.enable()
    if (stopTurn === -1) {
      disposed = true
      await reminder.stop()
      await reminder.settled()
    }
    monitor = true
    tap()
    for (let turn = 0; turn < 20; turn += 1) await Promise.resolve()
    await reminder.settled()
    expect(focusedWhileDisposed).toEqual(stopTurn === undefined ? [false] : [])
  })
}
