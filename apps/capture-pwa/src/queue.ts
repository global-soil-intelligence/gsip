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

export const indexedDbQueue = {
  list: queued,
  remove: removeQueued,
}
