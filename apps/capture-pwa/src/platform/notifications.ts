import type { LocalNotificationsPlugin } from '@capacitor/local-notifications'
import { isNativeApp } from './index'

/** One reserved, opaque ID. Neither the provider nor the OS receives queue/account data. */
export const SYNC_REMINDER_ID = 471031
export type ReminderPermission =
  'granted' | 'denied' | 'unknown' | 'unsupported'
/** Internal dispatch checks; no decision context is passed to the native SDK. */
export type ReminderIntent = {
  fresh(): Promise<boolean>
  local(): boolean
}
export type ReminderNotifications = {
  readonly supported: boolean
  checkPermission(currentIntent?: ReminderIntent): Promise<ReminderPermission>
  requestPermission(currentIntent: ReminderIntent): Promise<ReminderPermission>
  schedule(at: number, currentIntent: ReminderIntent): Promise<boolean>
  clear(currentIntent?: ReminderIntent): Promise<boolean>
  onTap(callback: () => void): Promise<() => Promise<void>>
}
type Plugin = Pick<
  LocalNotificationsPlugin,
  | 'checkPermissions'
  | 'requestPermissions'
  | 'schedule'
  | 'cancel'
  | 'removeDeliveredNotificationsById'
  | 'getPending'
  | 'getDeliveredNotifications'
  | 'addListener'
>
const unsupported: ReminderNotifications = {
  supported: false,
  checkPermission: async () => 'unsupported',
  requestPermission: async () => 'unsupported',
  schedule: async () => false,
  clear: async () => true,
  onTap: async () => async () => undefined,
}

/** Native-only lazy import: the web implementation and browser Notification API never run. */
export function selectReminderNotifications(
  native?: boolean,
  load: () => Promise<{ api: Plugin }> = () =>
    import('@capacitor/local-notifications').then((module) => ({
      api: module.LocalNotifications,
    })),
): ReminderNotifications {
  try {
    if (native === undefined ? !isNativeApp() : native !== true)
      return unsupported
  } catch {
    return unsupported
  }
  // Capacitor returns a Proxy whose synthetic `then` method must never be promise-assimilated.
  let loaded: Promise<{ api: Plugin }> | undefined
  const plugin = () =>
    (loaded ??= Promise.resolve()
      .then(load)
      .catch(() => {
        loaded = undefined
        throw new Error('Device reminders are unavailable.')
      }))
  const permission = async (
    request: boolean,
    currentIntent?: ReminderIntent,
  ): Promise<ReminderPermission> => {
    try {
      const api = (await plugin()).api
      if (
        (request && !currentIntent) ||
        (currentIntent &&
          (!(await currentIntent.fresh()) || !currentIntent.local()))
      )
        return 'unknown'
      const result = request
        ? await api.requestPermissions()
        : await api.checkPermissions()
      return result.display === 'granted'
        ? 'granted'
        : result.display === 'denied'
          ? 'denied'
          : 'unknown'
    } catch {
      return 'unknown'
    }
  }
  return {
    supported: true,
    checkPermission: (currentIntent) => permission(false, currentIntent),
    requestPermission: (currentIntent) => permission(true, currentIntent),
    async schedule(at, currentIntent) {
      if (!Number.isSafeInteger(at) || at <= Date.now()) return false
      try {
        const api = (await plugin()).api
        // A lazy-import await must not turn a stale click into a native prompt/alarm.
        if (!(await currentIntent.fresh()) || !currentIntent.local())
          return false
        const result = await api.schedule({
          notifications: [
            {
              id: SYNC_REMINDER_ID,
              title: 'GSIP sync reminder',
              body: 'Open GSIP to review unsynced work.',
              isExactNotification: false,
              isExactMandatory: false,
              schedule: {
                at: new Date(at),
                repeats: false,
                allowWhileIdle: false,
              },
            },
          ],
        })
        return (
          result.notifications.length === 1 &&
          result.notifications[0]?.id === SYNC_REMINDER_ID
        )
      } catch {
        return false
      }
    },
    async clear(currentIntent) {
      try {
        const api = (await plugin()).api
        const permitted = async () =>
          !currentIntent ||
          ((await currentIntent.fresh()) && currentIntent.local())
        if (!(await permitted()) || (currentIntent && !currentIntent.local()))
          return false
        await api.cancel({ notifications: [{ id: SYNC_REMINDER_ID }] })
        if (!(await permitted()) || (currentIntent && !currentIntent.local()))
          return false
        await api.removeDeliveredNotificationsById({ ids: [SYNC_REMINDER_ID] })
        if (!(await permitted()) || (currentIntent && !currentIntent.local()))
          return false
        const [pending, delivered] = await Promise.all([
          api.getPending(),
          api.getDeliveredNotifications(),
        ])
        return (
          !pending.notifications.some((item) => item.id === SYNC_REMINDER_ID) &&
          !delivered.notifications.some((item) => item.id === SYNC_REMINDER_ID)
        )
      } catch {
        return false
      }
    },
    async onTap(callback) {
      try {
        const handle = await (
          await plugin()
        ).api.addListener('localNotificationActionPerformed', (event) => {
          try {
            // Read only the owned ID. Never inspect/copy callback extras, URLs or action inputs.
            if (event.notification.id === SYNC_REMINDER_ID) callback()
          } catch {
            /* Native callback objects and errors stay private. */
          }
        })
        return async () => {
          try {
            await handle.remove()
          } catch {
            /* No plugin errors in UI/logs. */
          }
        }
      } catch {
        return async () => undefined
      }
    },
  }
}
