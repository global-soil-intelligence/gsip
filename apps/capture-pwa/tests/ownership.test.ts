import 'fake-indexeddb/auto'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AccountChanged, RecordWithdrawn } from '../src/errors'
import {
  clearQueue,
  discardHeld,
  enqueue,
  indexedDbQueue,
  queued,
  releaseHeld,
} from '../src/queue'
import { type GsipClient, recordOwner, submitQueued } from '../src/supabase'
import { drainQueue, isSyncEligible, type QueueStore } from '../src/sync'
import type { QueueRecord } from '../src/types'

function record(id: string, ownerUid?: string): QueueRecord {
  return {
    accuracyM: 7,
    attributionName: 'Anonymous soil contributor',
    capturedAt: '2026-10-01T00:00:00Z',
    deviceModel: 'test device',
    disturbed: false,
    grantId: `grant-${id}`,
    landCover: 'cropland',
    latitude: 40.446,
    longitude: -79.982,
    ownerUid,
    photos: [],
    queuedAt: '2026-10-01T00:00:00Z',
    submissionId: id,
    surfaceCondition: 'moist',
    termsVersion: '2026-07-22-v1',
  }
}

type Session = { error: Error | null; uid: string | null }

function client(
  session: Session,
  options: { grantError?: { code: string; message: string } } = {},
) {
  const calls: string[] = []
  const query = (table: string) => {
    const chain = {
      eq: () => chain,
      insert: async () => {
        calls.push(`insert:${table}`)
        return {
          error:
            table === 'contribution_grants'
              ? (options.grantError ?? null)
              : null,
        }
      },
      maybeSingle: async () => ({
        data: table === 'contributors' ? { id: 'contributor-1' } : null,
        error: null,
      }),
      select: () => chain,
    }
    return chain
  }
  const fake = {
    auth: {
      getSession: async () => ({
        data: { session: session.uid ? { user: { id: session.uid } } : null },
        error: session.error,
      }),
      signInAnonymously: async () => {
        calls.push('signInAnonymously')
        return { data: { user: { id: 'new-anonymous' } }, error: null }
      },
    },
    from: (table: string) => query(table),
  }
  return { calls, client: fake as unknown as GsipClient }
}

beforeEach(async () => {
  // Records were accepted on 2026-10-01; the clock is pinned inside the 30-day window (I9).
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-10-02T00:00:00Z'))
  await clearQueue()
  window.localStorage.clear()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('records are only ever sent as the account they were made under', () => {
  it('refuses to send a record under a different signed-in account', async () => {
    const { calls, client: other } = client({ error: null, uid: 'uid-b' })
    await expect(
      submitQueued(other, record('r1', 'uid-a')),
    ).rejects.toBeInstanceOf(AccountChanged)
    expect(calls).toEqual([])
  })

  it('never creates a new account for a record whose account is gone', async () => {
    const { calls, client: signedOut } = client({ error: null, uid: null })
    await expect(
      submitQueued(signedOut, record('r2', 'uid-a')),
    ).rejects.toBeInstanceOf(AccountChanged)
    expect(calls).not.toContain('signInAnonymously')
  })

  it('creates the anonymous account for a first sync on a new device', async () => {
    const { calls, client: fresh } = client({ error: null, uid: null })
    await submitQueued(fresh, record('r3')).catch(() => undefined)
    expect(calls[0]).toBe('signInAnonymously')
  })

  it('does not misattribute while the session cannot be read', async () => {
    const { calls, client: offline } = client({
      error: new Error('Failed to fetch'),
      uid: null,
    })
    await expect(submitQueued(offline, record('r4'))).rejects.toThrow(
      'Failed to fetch',
    )
    expect(calls).toEqual([])
  })

  it('turns a withdrawal refusal into a withdrawn record', async () => {
    const { client: owner } = client(
      { error: null, uid: 'uid-a' },
      { grantError: { code: 'WD001', message: 'withdrawn' } },
    )
    await expect(
      submitQueued(owner, record('r5', 'uid-a')),
    ).rejects.toBeInstanceOf(RecordWithdrawn)
  })

  it('stamps new records with the signed-in account, or the last one seen offline', async () => {
    const { client: online } = client({ error: null, uid: 'uid-a' })
    expect(await recordOwner(online)).toBe('uid-a')
    const { client: offline } = client({
      error: new Error('Failed to fetch'),
      uid: null,
    })
    expect(await recordOwner(offline)).toBe('uid-a')
    expect(await recordOwner(null)).toBeUndefined()
  })
})

describe('the drain', () => {
  it('drops withdrawn records and holds records of another account', async () => {
    await enqueue(record('withdrawn'))
    await enqueue(record('elsewhere', 'uid-a'))
    await enqueue(record('fine'))

    const summary = await drainQueue(indexedDbQueue, async (item) => {
      if (item.submissionId === 'withdrawn') throw new RecordWithdrawn()
      if (item.submissionId === 'elsewhere') throw new AccountChanged()
    })

    expect(summary).toEqual({
      discarded: 1,
      failed: 0,
      held: 1,
      reconfirm: 0,
      synced: 1,
    })
    const [held] = await queued()
    expect(held.submissionId).toBe('elsewhere')
    expect(held.heldAt).toBeDefined()
    expect(held.syncAttempts).toBeUndefined()
    expect(isSyncEligible(held)).toBe(false)
  })

  it('never writes back a record discarded while it was being sent', async () => {
    await enqueue(record('cleared'))
    const summary = await drainQueue(indexedDbQueue, async () => {
      await clearQueue()
      throw new Error('network dropped')
    })

    expect(summary.failed).toBe(0)
    expect(await queued()).toEqual([])
  })

  it('stops at once when the queue is cleared mid-drain', async () => {
    const sent: string[] = []
    let generation = 0
    const records = [record('one'), record('two')]
    const store: QueueStore = {
      generation: () => generation,
      list: async () => records,
      put: async () => undefined,
      remove: async () => undefined,
    }
    await drainQueue(store, async (item) => {
      sent.push(item.submissionId)
      generation += 1
    })
    expect(sent).toEqual(['one'])
  })

  it('lets the person discard held records or send them from the current account', async () => {
    await enqueue({ ...record('a', 'uid-a'), heldAt: '2026-10-10T00:00:00Z' })
    await enqueue({ ...record('b', 'uid-a'), heldAt: '2026-10-10T00:00:00Z' })
    await enqueue(record('c'))

    await releaseHeld()
    expect(
      (await queued()).map((item) => [
        item.submissionId,
        item.heldAt,
        item.ownerUid,
      ]),
    ).toEqual([
      ['a', undefined, undefined],
      ['b', undefined, undefined],
      ['c', undefined, undefined],
    ])

    await enqueue({ ...record('d', 'uid-a'), heldAt: '2026-10-10T00:00:00Z' })
    expect(await discardHeld()).toBe(1)
    expect((await queued()).map((item) => item.submissionId)).toEqual([
      'a',
      'b',
      'c',
    ])
  })
})
