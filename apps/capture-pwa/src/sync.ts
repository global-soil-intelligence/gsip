import {
  AccountChanged,
  LibraryConflict,
  LibraryUnavailable,
  QueueDiscarded,
  RecordWithdrawn,
  TermsReconfirmationNeeded,
} from './errors'
import type { QueueRecord } from './types'

export type QueueStore = {
  /** Changes when the queue is cleared; a drain never writes back into a cleared queue. */
  generation?: () => number
  revision?: () => Promise<number>
  isCurrent?: (revision: number) => Promise<boolean>
  putIfCurrent?: (record: QueueRecord, revision: number) => Promise<boolean>
  list: () => Promise<QueueRecord[]>
  put: (record: QueueRecord) => Promise<void>
  remove: (submissionId: string) => Promise<void>
}

export type SyncSummary = {
  discarded: number
  failed: number
  held: number
  /** Held until the person accepts the contribution terms again (I9). */
  reconfirm: number
  synced: number
  paused?: number
  conflicts?: number
}

export const MAX_SYNC_ATTEMPTS = 5
const INITIAL_RETRY_DELAY_MS = 30_000

export function isSyncEligible(
  record: QueueRecord,
  now: number = Date.now(),
): boolean {
  if (
    record.deadLetteredAt ||
    record.heldAt ||
    record.termsExpiredAt ||
    record.libraryConflictAt
  )
    return false
  if (!record.nextRetryAt) return true
  const retryAt = Date.parse(record.nextRetryAt)
  return !Number.isFinite(retryAt) || retryAt <= now
}

/**
 * Sends every eligible record once. A record its contributor withdrew is dropped (the server
 * refuses it for good); a record whose account is no longer signed in here is held for the
 * person to decide; anything else is retried with backoff and dead-lettered after five attempts.
 * Once `stopped` reports true (the screen that started the drain has closed), nothing more is
 * sent: the drain ends before its next record and leaves it queued.
 */
export async function drainQueue(
  store: QueueStore,
  send: (
    record: QueueRecord,
    checkpoint: (record: QueueRecord) => Promise<void>,
  ) => Promise<void>,
  now: () => number = Date.now,
  stopped: () => boolean = () => false,
): Promise<SyncSummary> {
  const locks = typeof navigator === 'undefined' ? undefined : navigator.locks
  if (!locks?.request) return drainUnlocked(store, send, now, stopped)
  // The browser owns this lock across tabs until the whole drain settles. A busy tab
  // returns immediately; the existing online/retry triggers may try again later.
  return locks.request('gsip-sync', { ifAvailable: true }, (lock) =>
    lock ? drainUnlocked(store, send, now, stopped) : emptySummary(),
  )
}

function emptySummary(): SyncSummary {
  return { discarded: 0, failed: 0, held: 0, reconfirm: 0, synced: 0 }
}

async function drainUnlocked(
  store: QueueStore,
  send: (
    record: QueueRecord,
    checkpoint: (record: QueueRecord) => Promise<void>,
  ) => Promise<void>,
  now: () => number,
  stopped: () => boolean,
): Promise<SyncSummary> {
  const summary = emptySummary()
  const generation = store.generation?.()
  const revision = await store.revision?.()
  const cleared = async () =>
    (store.generation !== undefined && store.generation() !== generation) ||
    (revision !== undefined &&
      store.isCurrent !== undefined &&
      !(await store.isCurrent(revision)))
  const write = async (record: QueueRecord): Promise<boolean> => {
    if (await cleared()) return false
    if (revision !== undefined && store.putIfCurrent)
      return store.putIfCurrent(record, revision)
    await store.put(record)
    return true
  }
  const checkpoint = async (record: QueueRecord) => {
    if (!(await write(record))) throw new QueueDiscarded()
  }
  for (const record of await store.list()) {
    if ((await cleared()) || stopped()) break
    const attemptStartedAt = now()
    if (!isSyncEligible(record, attemptStartedAt)) continue
    try {
      await send(record, checkpoint)
      if (await cleared()) break
      await store.remove(record.submissionId)
      summary.synced += 1
    } catch (error) {
      if ((await cleared()) || error instanceof QueueDiscarded) break
      if (error instanceof RecordWithdrawn) {
        await store.remove(record.submissionId)
        summary.discarded += 1
        continue
      }
      if (error instanceof LibraryUnavailable) {
        // A checkpoint may already contain completed photo stages; preserve it unchanged.
        summary.paused = (summary.paused ?? 0) + 1
        continue
      }
      if (error instanceof LibraryConflict) {
        if (
          !(await write({
            ...record,
            libraryConflictAt: new Date(attemptStartedAt).toISOString(),
          }))
        )
          break
        summary.conflicts = (summary.conflicts ?? 0) + 1
        continue
      }
      if (error instanceof AccountChanged) {
        if (
          !(await write({
            ...record,
            heldAt: new Date(attemptStartedAt).toISOString(),
          }))
        )
          break
        summary.held += 1
        continue
      }
      if (error instanceof TermsReconfirmationNeeded) {
        if (
          !(await write({
            ...record,
            termsExpiredAt: new Date(attemptStartedAt).toISOString(),
          }))
        )
          break
        summary.reconfirm += 1
        continue
      }
      const syncAttempts = (record.syncAttempts ?? 0) + 1
      const deadLettered = syncAttempts >= MAX_SYNC_ATTEMPTS
      const retryDelay =
        INITIAL_RETRY_DELAY_MS * 2 ** Math.max(0, syncAttempts - 1)
      if (
        !(await write({
          ...record,
          deadLetteredAt: deadLettered
            ? new Date(attemptStartedAt).toISOString()
            : undefined,
          nextRetryAt: deadLettered
            ? undefined
            : new Date(attemptStartedAt + retryDelay).toISOString(),
          syncAttempts,
        }))
      )
        break
      summary.failed += 1
    }
  }
  return summary
}
