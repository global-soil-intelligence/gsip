import { type DBSchema, type IDBPDatabase, openDB } from 'idb'
import type { QueueRecord } from './types'

interface CaptureQueueDatabase extends DBSchema {
  submissions: {
    key: string
    value: QueueRecord
  }
}

let databasePromise: Promise<IDBPDatabase<CaptureQueueDatabase>> | undefined

function database() {
  databasePromise ??= openDB<CaptureQueueDatabase>('gsip-capture-v1', 1, {
    upgrade(db) {
      db.createObjectStore('submissions', { keyPath: 'submissionId' })
    },
  })
  return databasePromise
}

export async function enqueue(record: QueueRecord): Promise<void> {
  await (await database()).put('submissions', record)
}

export async function queued(): Promise<QueueRecord[]> {
  return (await database()).getAll('submissions')
}

export async function removeQueued(submissionId: string): Promise<void> {
  await (await database()).delete('submissions', submissionId)
}

/** Discards every observation still queued on this device (WP-6d withdrawal and deletion). */
export async function clearQueue(): Promise<number> {
  const records = await queued()
  await (await database()).clear('submissions')
  return records.length
}

export async function retryDeadLettered(): Promise<void> {
  for (const record of await queued()) {
    if (!record.deadLetteredAt) continue
    await enqueue({
      ...record,
      deadLetteredAt: undefined,
      nextRetryAt: undefined,
      syncAttempts: 0,
    })
  }
}

export const indexedDbQueue = {
  list: queued,
  put: enqueue,
  remove: removeQueued,
}
