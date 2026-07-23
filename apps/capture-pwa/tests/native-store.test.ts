import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { QueueRecord } from '../src/types'
const state = vi.hoisted(() => ({
  files: new Map<string, string>(),
  failRename: false,
}))
vi.mock('@capacitor/filesystem', () => ({
  Directory: { Data: 'DATA' },
  Encoding: { UTF8: 'utf8' },
  Filesystem: {
    mkdir: async () => {},
    readdir: async () => ({
      files: [...state.files.keys()].map((path) => ({
        name: path.split('/').at(-1)!,
      })),
    }),
    writeFile: async ({ path, data }: { path: string; data: string }) => {
      state.files.set(path, data)
    },
    readFile: async ({ path }: { path: string }) => ({
      data: state.files.get(path),
    }),
    rename: async ({ from, to }: { from: string; to: string }) => {
      if (state.failRename) throw new Error('interrupted')
      state.files.set(to, state.files.get(from)!)
      state.files.delete(from)
    },
    deleteFile: async ({ path }: { path: string }) => {
      state.files.delete(path)
    },
  },
}))
import { nativeEnqueue, nativeQueued, nativeRemove } from '../src/nativeStore'
const record = {
  submissionId: 'native-1',
  latitude: 40,
  longitude: -79,
  draft: true,
  photos: [
    {
      bytes: new Uint8Array([255, 216, 255]),
      shotType: 'A',
      mimeType: 'image/jpeg',
      objectId: 'photo-1',
    },
  ],
} as QueueRecord
beforeEach(() => {
  state.files.clear()
  state.failRename = false
})
describe('durable native observations', () => {
  it('round-trips binary photos and private coordinates', async () => {
    await nativeEnqueue(record)
    expect(await nativeQueued()).toEqual([record])
  })
  it('preserves the last complete revision if a save is interrupted', async () => {
    await nativeEnqueue(record)
    state.failRename = true
    await expect(nativeEnqueue({ ...record, latitude: 41 })).rejects.toThrow(
      'interrupted',
    )
    expect(await nativeQueued()).toEqual([record])
    await nativeRemove(record.submissionId)
    expect(state.files.size).toBe(0)
  })
  it('serializes overlapping updates and removes obsolete private copies', async () => {
    await Promise.all([
      nativeEnqueue(record),
      nativeEnqueue({ ...record, latitude: 42 }),
    ])
    expect((await nativeQueued())[0].latitude).toBe(42)
    expect(state.files.size).toBe(1)
  })
})
