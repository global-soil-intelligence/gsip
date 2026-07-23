import { Directory, Encoding, Filesystem } from '@capacitor/filesystem'
import type { QueueRecord } from './types'

const directory = Directory.Data
const root = 'gsip-observations'
type DiskRecord = Omit<QueueRecord, 'photos'> & {
  photos: Array<
    Omit<QueueRecord['photos'][number], 'bytes'> & { bytes: number[] }
  >
}

async function entries() {
  await Filesystem.mkdir({ directory, path: root, recursive: true }).catch(
    () => {},
  )
  return (await Filesystem.readdir({ directory, path: root })).files
}

export async function nativeQueued(): Promise<QueueRecord[]> {
  const latest = new Map<string, QueueRecord>()
  for (const file of (await entries())
    .filter((f) => f.name.endsWith('.json'))
    .sort((a, b) => a.name.localeCompare(b.name))) {
    const result = await Filesystem.readFile({
      directory,
      path: `${root}/${file.name}`,
      encoding: Encoding.UTF8,
    })
    const record = JSON.parse(String(result.data)) as DiskRecord
    latest.set(record.submissionId, {
      ...record,
      photos: record.photos.map((p) => ({
        ...p,
        bytes: new Uint8Array(p.bytes),
      })),
    })
  }
  return [...latest.values()]
}

// Append a complete revision, verify it, then retire older versions. An interrupted
// write never overwrites the last complete observation. Temporary files are ignored.
async function writeRevision(record: QueueRecord): Promise<void> {
  const old = (await entries()).filter((f) =>
    f.name.startsWith(`${record.submissionId}-`),
  )
  const name = `${record.submissionId}-${Date.now()}-${crypto.randomUUID()}.json`
  const path = `${root}/${name}`
  const data = JSON.stringify({
    ...record,
    photos: record.photos.map((p) => ({ ...p, bytes: Array.from(p.bytes) })),
  })
  await Filesystem.writeFile({
    directory,
    path: `${path}.tmp`,
    data,
    encoding: Encoding.UTF8,
    recursive: true,
  })
  const verified = await Filesystem.readFile({
    directory,
    path: `${path}.tmp`,
    encoding: Encoding.UTF8,
  })
  if (verified.data !== data)
    throw new Error('The observation could not be saved. Please retry.')
  await Filesystem.rename({ directory, from: `${path}.tmp`, to: path })
  for (const file of old)
    await Filesystem.deleteFile({ directory, path: `${root}/${file.name}` })
}

export async function nativeRemove(id: string): Promise<void> {
  for (const file of (await entries()).filter((f) =>
    f.name.startsWith(`${id}-`),
  )) {
    await Filesystem.deleteFile({ directory, path: `${root}/${file.name}` })
  }
}

let writing = Promise.resolve()
export function nativeEnqueue(record: QueueRecord): Promise<void> {
  const next = writing.then(() => writeRevision(record))
  writing = next.catch(() => {})
  return next
}
