import type {
  ReminderIntent,
  ReminderNotifications,
} from './platform/notifications'

export const REMINDER_DELAY = 24 * 60 * 60 * 1000
export type ReminderContext = {
  owner: string | null
  captureLive: boolean
  gate: 'open' | 'closed' | 'unknown'
  revision: number
  hasWork: boolean
  blocked: boolean
}
/** Private intent only; never store a session/token, queue record, photo or point here. */
export type SyncReminderState = {
  owner: string | null
  enabled: boolean
  epoch: number
  revision: number
  cycleOpen: boolean
  consumed: boolean
  allowed: boolean
  blocked: boolean
  cleanupPending: boolean
}
export const initialReminderState = (): SyncReminderState => ({
  owner: null,
  enabled: false,
  epoch: 0,
  revision: 0,
  cycleOpen: false,
  consumed: false,
  allowed: false,
  blocked: true,
  cleanupPending: true,
})
export type ReminderStore = {
  read(): Promise<SyncReminderState>
  update(
    change: (state: SyncReminderState) => SyncReminderState,
  ): Promise<SyncReminderState>
}
export type ReminderOutcome =
  | 'off'
  | 'on'
  | 'held'
  | 'unsupported'
  | 'permission_denied'
  | 'cleanup_pending'
export type ReminderView = { enabled: boolean; outcome: ReminderOutcome }
export type ReminderLock = <T>(run: () => Promise<T>) => Promise<T | undefined>

/** A native scheduling operation requires a cross-context lock. Unsupported devices hold. */
export const reminderLock: ReminderLock = async (run) => {
  if (typeof navigator === 'undefined' || !navigator.locks?.request)
    return undefined
  return navigator.locks.request('gsip-sync-reminder', run)
}
function allowed(context: ReminderContext): boolean {
  return (
    context.captureLive && context.gate === 'open' && Boolean(context.owner)
  )
}

/**
 * One inexact reminder per backlog cycle. Durable fences precede plugin calls; late schedule
 * completion is cleared before the next native operation. No timer, retry loop or remote I/O.
 */
export function createSyncReminder({
  notifications,
  store,
  context,
  focusQueue,
  changed = () => undefined,
  lock = reminderLock,
  now = () => Date.now(),
}: {
  notifications: ReminderNotifications
  store: ReminderStore
  context: () => Promise<ReminderContext>
  focusQueue: () => void
  changed?: (view: ReminderView) => void
  lock?: ReminderLock
  now?: () => number
}) {
  let version = 0
  let stopped = false
  let lifetime = 0
  let operations: Promise<unknown> = Promise.resolve()
  let removeListener: (() => Promise<void>) | undefined
  const active = (expected: number) => !stopped && lifetime === expected
  const report = (state: SyncReminderState, outcome: ReminderOutcome) => {
    if (stopped) return
    try {
      changed({ enabled: state.enabled, outcome })
    } catch {
      /* No callback details escape. */
    }
  }
  const read = async (expected: number) => {
    if (!active(expected)) return undefined
    const state = await store.read()
    return active(expected) ? state : undefined
  }
  const update = async (
    expected: number,
    change: (state: SyncReminderState) => SyncReminderState,
  ) => {
    if (!active(expected)) return undefined
    const state = await store.update((previous) =>
      active(expected) ? change(previous) : previous,
    )
    return active(expected) ? state : undefined
  }
  const observe = async (expected: number) => {
    if (!active(expected)) return undefined
    const decision = await context()
    if (!active(expected)) return undefined
    return update(expected, (previous) => {
      const ownerChanged = previous.owner !== decision.owner
      const changed =
        ownerChanged ||
        previous.revision !== decision.revision ||
        previous.cycleOpen !== decision.hasWork ||
        previous.allowed !== allowed(decision) ||
        previous.blocked !== decision.blocked
      if (!changed) return previous
      return {
        ...previous,
        owner: decision.owner,
        enabled: ownerChanged ? false : previous.enabled,
        revision: decision.revision,
        cycleOpen: decision.hasWork,
        consumed:
          decision.hasWork && previous.cycleOpen ? previous.consumed : false,
        allowed: allowed(decision),
        blocked: decision.blocked,
        epoch: previous.epoch + 1,
        cleanupPending: true,
      }
    })
  }
  const current = async (
    epoch: number,
    expectedVersion: number,
    expected: number,
  ) => {
    if (!active(expected) || version !== expectedVersion) return false
    const state = await observe(expected)
    return Boolean(
      state &&
      active(expected) &&
      version === expectedVersion &&
      state.epoch === epoch,
    )
  }
  const intent = (
    epoch: number,
    expectedVersion: number,
    owner: string | null,
    expected: number,
    permissionRequest = false,
  ): ReminderIntent => ({
    local: () => active(expected) && version === expectedVersion,
    async fresh() {
      if (!(await current(epoch, expectedVersion, expected))) return false
      const state = await read(expected)
      return Boolean(
        state &&
        active(expected) &&
        version === expectedVersion &&
        state.epoch === epoch &&
        state.owner === owner &&
        state.allowed &&
        !state.blocked &&
        (permissionRequest
          ? !state.cleanupPending
          : state.enabled && state.cycleOpen && state.consumed),
      )
    },
  })
  type Scope = Pick<SyncReminderState, 'epoch' | 'owner'>
  const matches = (state: SyncReminderState, scope: Scope) =>
    state.epoch === scope.epoch && state.owner === scope.owner
  const activityIntent = (expected: number, scope: Scope): ReminderIntent => ({
    local: () => active(expected),
    async fresh() {
      const state = await read(expected)
      return Boolean(state && matches(state, scope))
    },
  })
  /** Cleanup owns the persisted generation it fenced, never whatever a replacement owns now. */
  const clear = async (expected: number, owned?: Scope): Promise<boolean> => {
    const permitted = () => (owned ? lifetime === expected : active(expected))
    if (!permitted()) return false
    const before = await store.read()
    if (!permitted() || (owned && !matches(before, owned))) return false
    if (!before.cleanupPending) {
      const marked = await store.update((state) =>
        permitted() && matches(state, before)
          ? { ...state, cleanupPending: true }
          : state,
      )
      if (!permitted() || !matches(marked, before)) return false
    }
    const cleanupIntent: ReminderIntent = {
      local: permitted,
      async fresh() {
        if (!permitted()) return false
        const state = await store.read()
        return permitted() && matches(state, before)
      },
    }
    const absent = await notifications.clear(cleanupIntent)
    if (!permitted()) return false
    let committed = false
    const state = await store.update((latest) => {
      if (!permitted() || !matches(latest, before)) return latest
      committed = true
      return absent ? { ...latest, cleanupPending: false } : latest
    })
    if (!permitted() || !committed) return false
    if (state.cleanupPending) report(state, 'cleanup_pending')
    return absent && !state.cleanupPending
  }
  const serial = (
    run: () => Promise<void>,
    expected = lifetime,
    detached = false,
  ): Promise<void> => {
    if (!detached && !active(expected)) return Promise.resolve()
    const next = operations.then(async () => {
      if (!detached && !active(expected)) return
      try {
        const result = await lock(async () => {
          if (!detached && !active(expected)) return false
          await run()
          return true
        })
        if (result === undefined && !detached && active(expected)) {
          const absent = await clear(expected),
            state = await read(expected)
          if (state) report(state, absent ? 'unsupported' : 'cleanup_pending')
        }
      } catch {
        if (detached || !active(expected)) return
        try {
          const state = await update(expected, (previous) => ({
            ...previous,
            cleanupPending: true,
          }))
          if (state) report(state, 'cleanup_pending')
        } catch {
          /* Persistence uncertainty stays held; private errors never reach UI/logs. */
        }
      }
    })
    operations = next
    return next
  }
  const reconcile = async (expected: number) => {
    if (!active(expected)) return
    const expectedVersion = version
    let state = await observe(expected)
    if (!state) return
    if (state.cleanupPending && !(await clear(expected))) return
    state = await read(expected)
    if (!state) return
    if (!state.enabled || !state.allowed || !state.cycleOpen || state.blocked) {
      report(state, state.enabled ? 'held' : 'off')
      return
    }
    const permission = await notifications.checkPermission(
      activityIntent(expected, state),
    )
    if (!active(expected)) return
    if (!(await current(state.epoch, expectedVersion, expected))) {
      await clear(expected)
      return
    }
    if (permission !== 'granted') {
      const marked = await update(expected, (latest) => ({
        ...latest,
        cleanupPending: true,
      }))
      if (!marked) return
      await clear(expected)
      const latest = await read(expected)
      if (latest) report(latest, 'held')
      return
    }
    if (state.consumed) {
      report(state, 'on')
      return
    }
    const reserved = await update(expected, (latest) =>
      latest.epoch === state.epoch && !latest.consumed
        ? { ...latest, consumed: true, cleanupPending: true }
        : latest,
    )
    if (!reserved) return
    if (
      !(await current(state.epoch, expectedVersion, expected)) ||
      !reserved.consumed
    ) {
      await clear(expected)
      return
    }
    const scheduled = await notifications.schedule(
      now() + REMINDER_DELAY,
      intent(state.epoch, expectedVersion, state.owner, expected),
    )
    // Stop already persisted a scoped cleanup behind this operation. A stale continuation
    // must not clear a replacement's generation; late completion is handled by that owned fence.
    if (!active(expected)) return
    if (
      !scheduled ||
      !(await current(state.epoch, expectedVersion, expected))
    ) {
      await clear(expected)
      return
    }
    const committed = await update(expected, (latest) =>
      latest.epoch === state.epoch
        ? { ...latest, cleanupPending: false }
        : latest,
    )
    if (!committed) return
    if (committed.cleanupPending) await clear(expected)
    else report(committed, 'on')
  }
  /** Durable intent precedes plugin cleanup, so rights never await a lost native reply. */
  const invalidate = async (
    disable = false,
    expected = lifetime,
    stopping = false,
  ) => {
    const permitted = () => lifetime === expected && (stopping || !stopped)
    if (!permitted()) return
    version += 1
    let committed = false
    try {
      const state = await store.update((previous) => {
        if (!permitted()) return previous
        committed = true
        return {
          ...previous,
          epoch: previous.epoch + 1,
          cleanupPending: true,
          enabled: disable ? false : previous.enabled,
        }
      })
      if (!committed || !permitted()) return
      report(state, disable ? 'off' : 'cleanup_pending')
      void serial(
        async () => {
          await clear(expected, state)
        },
        expected,
        true,
      )
    } catch {
      if (permitted()) report(initialReminderState(), 'cleanup_pending')
    }
  }
  return {
    async start() {
      if (!notifications.supported) {
        report(initialReminderState(), 'unsupported')
        return
      }
      stopped = false
      const expected = ++lifetime,
        previousListener = removeListener
      removeListener = undefined
      if (previousListener)
        void serial(
          async () => {
            await previousListener()
          },
          expected,
          true,
        )
      await invalidate(false, expected)
      await serial(async () => {
        if (!active(expected)) return
        const registered = await notifications.onTap(() => {
          if (!active(expected)) return
          void serial(async () => {
            const state = await observe(expected)
            if (
              !state ||
              !state.enabled ||
              !state.allowed ||
              state.blocked ||
              !state.cycleOpen
            )
              return
            const permission = await notifications.checkPermission(
              activityIntent(expected, state),
            )
            if (!active(expected) || permission !== 'granted') return
            const fresh = await observe(expected)
            if (active(expected) && fresh && fresh.epoch === state.epoch)
              focusQueue()
          }, expected)
        })
        if (!active(expected)) {
          await registered()
          return
        }
        removeListener = registered
        await reconcile(expected)
      }, expected)
    },
    refresh() {
      const expected = lifetime
      return notifications.supported && active(expected)
        ? serial(() => reconcile(expected), expected)
        : Promise.resolve()
    },
    async enable() {
      const expected = lifetime
      if (!active(expected)) return
      if (!notifications.supported) {
        report(initialReminderState(), 'unsupported')
        return
      }
      const expectedVersion = version + 1
      await invalidate(true, expected)
      await serial(async () => {
        let state = await observe(expected)
        if (!state) return
        if (version !== expectedVersion || !state.allowed || state.blocked) {
          report(state, 'held')
          return
        }
        if (state.cleanupPending && !(await clear(expected))) return
        state = await read(expected)
        if (!state) return
        if (!(await current(state.epoch, expectedVersion, expected))) {
          await clear(expected)
          return
        }
        const permission = await notifications.requestPermission(
          intent(state.epoch, expectedVersion, state.owner, expected, true),
        )
        if (!active(expected)) return
        if (!(await current(state.epoch, expectedVersion, expected))) {
          await clear(expected)
          return
        }
        if (permission !== 'granted') {
          report(state, 'permission_denied')
          return
        }
        const enabled = await update(expected, (latest) =>
          latest.epoch === state.epoch && version === expectedVersion
            ? { ...latest, enabled: true }
            : latest,
        )
        if (enabled) await reconcile(expected)
      }, expected)
    },
    disable() {
      return invalidate(true)
    },
    hold() {
      return invalidate(true)
    },
    gatesChanged() {
      return invalidate()
    },
    async synced() {
      const expected = lifetime
      if (!active(expected)) return
      await invalidate(false, expected)
      await serial(() => reconcile(expected), expected)
    },
    async stop() {
      if (stopped) return
      stopped = true
      const expected = ++lifetime,
        previousListener = removeListener
      removeListener = undefined
      await invalidate(false, expected, true)
      // This handle belongs only to the old registration, so removal cannot affect a new one.
      void serial(
        async () => {
          await previousListener?.()
        },
        expected,
        true,
      )
    },
    settled() {
      return operations.then(() => undefined)
    },
  }
}
