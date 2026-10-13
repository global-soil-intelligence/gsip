import type { LocalNotificationsPlugin } from '@capacitor/local-notifications'
import { expect, it, vi } from 'vitest'
import {
  selectReminderNotifications,
  SYNC_REMINDER_ID,
  type ReminderIntent,
} from '../src/platform/notifications'

const permittedIntent: ReminderIntent = {
  fresh: async () => true,
  local: () => true,
}
function fixture() {
  const plugin = {
    checkPermissions: vi.fn(async () => ({ display: 'granted' })),
    requestPermissions: vi.fn(async () => ({ display: 'granted' })),
    schedule: vi.fn(async () => ({
      notifications: [{ id: SYNC_REMINDER_ID }],
    })),
    cancel: vi.fn(async () => undefined),
    removeDeliveredNotificationsById: vi.fn(async () => undefined),
    getPending: vi.fn(async () => ({ notifications: [] as { id: number }[] })),
    getDeliveredNotifications: vi.fn(async () => ({
      notifications: [] as { id: number }[],
    })),
    addListener: vi.fn(async () => ({ remove: vi.fn(async () => undefined) })),
  }
  const load = vi.fn(async () => ({
    api: plugin as unknown as LocalNotificationsPlugin,
  }))
  return {
    plugin,
    load,
    notifications: selectReminderNotifications(true, load),
  }
}
it('web never imports a plugin or touches browser permissions even if every method is called', async () => {
  const load = vi.fn(async (): Promise<{ api: LocalNotificationsPlugin }> => {
    throw new Error('must not load')
  })
  const notifications = selectReminderNotifications(false, load)
  expect(notifications.supported).toBe(false)
  expect(await notifications.checkPermission()).toBe('unsupported')
  expect(await notifications.requestPermission(permittedIntent)).toBe(
    'unsupported',
  )
  expect(
    await notifications.schedule(Date.now() + 86400000, permittedIntent),
  ).toBe(false)
  expect(await notifications.clear()).toBe(true)
  await (
    await notifications.onTap(() => {
      throw new Error('must not call')
    })
  )()
  expect(load).not.toHaveBeenCalled()
})
it('native provider constructs only one fixed generic inexact nonwaking one-shot payload', async () => {
  const f = fixture(),
    at = Date.now() + 86400000
  expect(f.load).not.toHaveBeenCalled()
  expect(await f.notifications.schedule(at, permittedIntent)).toBe(true)
  expect(f.plugin.schedule).toHaveBeenCalledExactlyOnceWith({
    notifications: [
      {
        id: SYNC_REMINDER_ID,
        title: 'GSIP sync reminder',
        body: 'Open GSIP to review unsynced work.',
        isExactNotification: false,
        isExactMandatory: false,
        schedule: { at: new Date(at), repeats: false, allowWhileIdle: false },
      },
    ],
  })
  expect(
    await f.notifications.schedule(
      {
        extra: 'fictional-private-canary',
      } as unknown as number,
      permittedIntent,
    ),
  ).toBe(false)
  expect(await f.notifications.schedule(0, permittedIntent)).toBe(false)
  expect(f.plugin.schedule).toHaveBeenCalledTimes(1)
})
it('cleanup cancels/removes only the owned ID then verifies pending AND delivered absence', async () => {
  const f = fixture()
  expect(await f.notifications.clear()).toBe(true)
  expect(f.plugin.cancel).toHaveBeenCalledExactlyOnceWith({
    notifications: [{ id: SYNC_REMINDER_ID }],
  })
  expect(
    f.plugin.removeDeliveredNotificationsById,
  ).toHaveBeenCalledExactlyOnceWith({ ids: [SYNC_REMINDER_ID] })
  f.plugin.getPending.mockResolvedValue({
    notifications: [{ id: SYNC_REMINDER_ID }],
  })
  expect(await f.notifications.clear()).toBe(false)
  f.plugin.getPending.mockResolvedValue({ notifications: [{ id: 2 }] })
  f.plugin.getDeliveredNotifications.mockResolvedValue({
    notifications: [{ id: SYNC_REMINDER_ID }],
  })
  expect(await f.notifications.clear()).toBe(false)
  f.plugin.getDeliveredNotifications.mockResolvedValue({
    notifications: [{ id: 2 }],
  })
  expect(await f.notifications.clear()).toBe(true)
})
it('native getter/SDK errors return only generic outcomes and never log canaries', async () => {
  const f = fixture(),
    log = vi.spyOn(console, 'error')
  f.plugin.checkPermissions.mockRejectedValue(
    new Error('fictional-private-canary', { cause: 'fictional-private-cause' }),
  )
  expect(await f.notifications.checkPermission()).toBe('unknown')
  f.plugin.schedule.mockRejectedValue(new Error('fictional-private-canary'))
  expect(
    await f.notifications.schedule(Date.now() + 86400000, permittedIntent),
  ).toBe(false)
  f.plugin.getPending.mockResolvedValue(
    Object.defineProperty({}, 'notifications', {
      get() {
        throw new Error('fictional-private-canary')
      },
    }) as { notifications: { id: number }[] },
  )
  expect(await f.notifications.clear()).toBe(false)
  expect(log).not.toHaveBeenCalled()
  log.mockRestore()
})
it('only the owned tap ID invokes a zero-argument callback; injected extras are never read', async () => {
  const f = fixture(),
    callback = vi.fn()
  const remove = await f.notifications.onTap(callback)
  const listener = f.plugin.addListener.mock.calls[0] as unknown as [
    string,
    (event: unknown) => void,
  ]
  expect(listener[0]).toBe('localNotificationActionPerformed')
  listener[1]({ notification: { id: 2 }, extra: 'https://fictional.invalid' })
  listener[1]({
    notification: {
      id: SYNC_REMINDER_ID,
      get extra() {
        throw new Error('private canary')
      },
    },
    get actionId() {
      throw new Error('private canary')
    },
  })
  listener[1]({
    get notification() {
      throw new Error('private canary')
    },
  })
  expect(callback).toHaveBeenCalledExactlyOnceWith()
  await remove()
  expect(
    (await f.plugin.addListener.mock.results[0].value).remove,
  ).toHaveBeenCalledTimes(1)
})

it('a changed intent during lazy import prevents a native permission request or schedule', async () => {
  for (const action of ['permission', 'schedule']) {
    const f = fixture()
    let resolve!: (plugin: { api: LocalNotificationsPlugin }) => void
    const loaded = new Promise<{ api: LocalNotificationsPlugin }>((done) => {
      resolve = done
    })
    const notifications = selectReminderNotifications(true, () => loaded)
    let current = true
    const pending =
      action === 'permission'
        ? notifications.requestPermission({
            fresh: async () => current,
            local: () => current,
          })
        : notifications.schedule(Date.now() + 86400000, {
            fresh: async () => current,
            local: () => current,
          })
    current = false
    resolve({ api: f.plugin as unknown as LocalNotificationsPlugin })
    await pending
    expect(f.plugin.requestPermissions).not.toHaveBeenCalled()
    expect(f.plugin.schedule).not.toHaveBeenCalled()
  }
})
it('invalid native-selection values are unsupported without loading a plugin', async () => {
  const f = fixture()
  const notifications = selectReminderNotifications(
    { synthetic: true } as unknown as boolean,
    f.load,
  )
  expect(notifications.supported).toBe(false)
  await notifications.checkPermission()
  expect(f.load).not.toHaveBeenCalled()
})

it('the lazy boundary boxes Capacitor plugin Proxies instead of promise-assimilating their synthetic then', async () => {
  const f = fixture()
  const api = new Proxy(f.plugin, {
    get(target, key, receiver) {
      if (key === 'then')
        throw new Error('must not inspect a plugin then method')
      return Reflect.get(target, key, receiver)
    },
  }) as unknown as LocalNotificationsPlugin
  const notifications = selectReminderNotifications(true, async () => ({ api }))
  expect(await notifications.checkPermission()).toBe('granted')
  expect(await notifications.clear()).toBe(true)
  expect(
    await notifications.schedule(Date.now() + 86400000, permittedIntent),
  ).toBe(true)
})
it('after a fresh durable check yields, the final local epoch fence still prevents native dispatch', async () => {
  for (const action of ['permission', 'schedule']) {
    const f = fixture()
    let resolve!: (allowed: boolean) => void, entered!: () => void
    const began = new Promise<void>((done) => {
      entered = done
    })
    const checked = new Promise<boolean>((done) => {
      resolve = done
    })
    let current = true
    const intent: ReminderIntent = {
      fresh: () => {
        entered()
        return checked
      },
      local: () => current,
    }
    const pending =
      action === 'permission'
        ? f.notifications.requestPermission(intent)
        : f.notifications.schedule(Date.now() + 86400000, intent)
    await began
    current = false
    resolve(true)
    await pending
    expect(f.plugin.requestPermissions).not.toHaveBeenCalled()
    expect(f.plugin.schedule).not.toHaveBeenCalled()
  }
})
it('scoped cleanup whose authority changes during plugin await never cancels a replacement reminder', async () => {
  const f = fixture()
  await f.notifications.checkPermission()
  let current = true
  const pending = f.notifications.clear({
    fresh: async () => current,
    local: () => current,
  })
  current = false
  expect(await pending).toBe(false)
  expect(f.plugin.cancel).not.toHaveBeenCalled()
  expect(f.plugin.removeDeliveredNotificationsById).not.toHaveBeenCalled()
})
it('scoped cleanup stops after a lost generation instead of removing replacement delivered notifications', async () => {
  const f = fixture()
  let current = true
  f.plugin.cancel.mockImplementation(async () => {
    current = false
  })
  expect(
    await f.notifications.clear({
      fresh: async () => current,
      local: () => current,
    }),
  ).toBe(false)
  expect(f.plugin.cancel).toHaveBeenCalledTimes(1)
  expect(f.plugin.removeDeliveredNotificationsById).not.toHaveBeenCalled()
  expect(f.plugin.getPending).not.toHaveBeenCalled()
})
