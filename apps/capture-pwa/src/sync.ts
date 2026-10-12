import { AccountChanged, RecordWithdrawn } from './errors'
import type { QueueRecord } from './types'

export type QueueStore = {
  /** Changes when the queue is cleared; a drain never writes back into a cleared queue. */
  generation?: () => number
  list: () => Promise<QueueRecord[]>
  put: (record: QueueRecord) => Promise<void>
  remove: (submissionId: string) => Promise<void>
}

export type SyncSummary = {
  discarded: number
  failed: number
  held: number
  synced: number
}

export const MAX_SYNC_ATTEMPTS = 5
const INITIAL_RETRY_DELAY_MS = 30_000

export function isSyncEligible(
  record: QueueRecord,
  now: number = Date.now(),
): boolean {
  if (record.deadLetteredAt || record.heldAt) return false
  if (!record.nextRetryAt) return true
  const retryAt = Date.parse(record.nextRetryAt)
  return !Number.isFinite(retryAt) || retryAt <= now
}

/**
 * Sends every eligible record once. A record its contributor withdrew is dropped (the server
 * refuses it for good); a record whose account is no longer signed in here is held for the
 * person to decide; anything else is retried with backoff and dead-lettered after five attempts.
 */
export async function drainQueue(
  store: QueueStore,
  send: (record: QueueRecord) => Promise<void>,
  now: () => number = Date.now,
): Promise<SyncSummary> {
  const summary: SyncSummary = { discarded: 0, failed: 0, held: 0, synced: 0 }
  const generation = store.generation?.()
  const cleared = () =>
    store.generation !== undefined && store.generation() !== generation
  for (const record of await store.list()) {
    if (cleared()) break
    const attemptStartedAt = now()
    if (!isSyncEligible(record, attemptStartedAt)) continue
    try {
      await send(record)
      await store.remove(record.submissionId)
      summary.synced += 1
    } catch (error) {
      if (error instanceof RecordWithdrawn) {
        await store.remove(record.submissionId)
        summary.discarded += 1
        continue
      }
      if (cleared()) break
      if (error instanceof AccountChanged) {
        await store.put({
          ...record,
          heldAt: new Date(attemptStartedAt).toISOString(),
        })
        summary.held += 1
        continue
      }
      const syncAttempts = (record.syncAttempts ?? 0) + 1
      const deadLettered = syncAttempts >= MAX_SYNC_ATTEMPTS
      const retryDelay =
        INITIAL_RETRY_DELAY_MS * 2 ** Math.max(0, syncAttempts - 1)
      await store.put({
        ...record,
        deadLetteredAt: deadLettered
          ? new Date(attemptStartedAt).toISOString()
          : undefined,
        nextRetryAt: deadLettered
          ? undefined
          : new Date(attemptStartedAt + retryDelay).toISOString(),
        syncAttempts,
      })
      summary.failed += 1
    }
  }
  return summary
}
