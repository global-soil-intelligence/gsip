import type { QueueRecord } from './types'

export type QueueStore = {
  list: () => Promise<QueueRecord[]>
  put: (record: QueueRecord) => Promise<void>
  remove: (submissionId: string) => Promise<void>
}

export type SyncSummary = { failed: number; synced: number }

export const MAX_SYNC_ATTEMPTS = 5
const INITIAL_RETRY_DELAY_MS = 30_000

export function isSyncEligible(
  record: QueueRecord,
  now: number = Date.now(),
): boolean {
  if (record.deadLetteredAt) return false
  if (!record.nextRetryAt) return true
  const retryAt = Date.parse(record.nextRetryAt)
  return !Number.isFinite(retryAt) || retryAt <= now
}

export async function drainQueue(
  store: QueueStore,
  send: (record: QueueRecord) => Promise<void>,
  now: () => number = Date.now,
): Promise<SyncSummary> {
  const summary: SyncSummary = { failed: 0, synced: 0 }
  for (const record of await store.list()) {
    const attemptStartedAt = now()
    if (!isSyncEligible(record, attemptStartedAt)) continue
    try {
      await send(record)
      await store.remove(record.submissionId)
      summary.synced += 1
    } catch {
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
