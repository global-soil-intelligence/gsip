import type { QueueRecord } from './types'

export type QueueStore = {
  list: () => Promise<QueueRecord[]>
  remove: (submissionId: string) => Promise<void>
}

export type SyncSummary = { failed: number; synced: number }

export async function drainQueue(
  store: QueueStore,
  send: (record: QueueRecord) => Promise<void>,
): Promise<SyncSummary> {
  const summary: SyncSummary = { failed: 0, synced: 0 }
  for (const record of await store.list()) {
    try {
      await send(record)
      await store.remove(record.submissionId)
      summary.synced += 1
    } catch {
      summary.failed += 1
    }
  }
  return summary
}
