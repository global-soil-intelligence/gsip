import { describe, expect, it } from 'vitest'
import {
  type GsipClient,
  latestDeletionRequest,
  requestDeletion,
} from '../src/supabase'

type Options = {
  contributor?: boolean
  insertError?: { code: string; message: string }
  latest?: Record<string, unknown> | null
  session?: boolean
}

function fakeClient({
  contributor = true,
  insertError,
  latest = null,
  session = true,
}: Options) {
  const calls: string[] = []
  const client = {
    auth: {
      getSession: async () => ({
        data: { session: session ? { user: { id: 'uid-1' } } : null },
      }),
      signInAnonymously: async () => {
        throw new Error('a rights request must never create an account')
      },
      signOut: async (options: { scope: string }) => {
        calls.push(`signOut:${options.scope}`)
        return { error: null }
      },
    },
    from(table: string) {
      calls.push(`from:${table}`)
      const query = {
        eq: () => query,
        insert: async (payload: unknown) => {
          calls.push(`insert:${table}:${JSON.stringify(payload)}`)
          return { error: insertError ?? null }
        },
        limit: () => query,
        maybeSingle: async () =>
          table === 'contributors'
            ? {
                data: contributor ? { id: 'contributor-1' } : null,
                error: null,
              }
            : { data: latest, error: null },
        order: () => query,
        select: () => query,
      }
      return query
    },
  }
  return { calls, client: client as unknown as GsipClient }
}

describe('rights requests', () => {
  it('reports nothing stored, without signing in, when this device never synced', async () => {
    const { calls, client } = fakeClient({ session: false })
    expect(await requestDeletion(client, 'delete_account')).toBe(
      'nothing_stored',
    )
    expect(await latestDeletionRequest(client)).toBeNull()
    expect(calls).toEqual([])
  })

  it('reports nothing stored for a session that never became a contributor', async () => {
    const { calls, client } = fakeClient({ contributor: false })
    expect(await requestDeletion(client, 'withdraw_contributions')).toBe(
      'nothing_stored',
    )
    expect(calls.some((call) => call.startsWith('insert:'))).toBe(false)
  })

  it('files a withdrawal for the signed-in contributor and stays signed in', async () => {
    const { calls, client } = fakeClient({})
    expect(await requestDeletion(client, 'withdraw_contributions')).toBe(
      'requested',
    )
    expect(calls).toContain(
      'insert:deletion_requests:{"contributor_id":"contributor-1","kind":"withdraw_contributions"}',
    )
    expect(calls.some((call) => call.startsWith('signOut'))).toBe(false)
  })

  it('signs this device out after filing an account deletion', async () => {
    const { calls, client } = fakeClient({})
    expect(await requestDeletion(client, 'delete_account')).toBe('requested')
    expect(calls.at(-1)).toBe('signOut:local')
  })

  it('recognizes a request that is already open', async () => {
    const { calls, client } = fakeClient({
      insertError: { code: '23505', message: 'duplicate key' },
    })
    expect(await requestDeletion(client, 'delete_account')).toBe('already_open')
    expect(calls.some((call) => call.startsWith('signOut'))).toBe(false)
  })

  it('surfaces any other failure', async () => {
    const { client } = fakeClient({
      insertError: { code: '42501', message: 'denied' },
    })
    await expect(
      requestDeletion(client, 'withdraw_contributions'),
    ).rejects.toMatchObject({ code: '42501' })
  })

  it('reads the latest request status', async () => {
    const { client } = fakeClient({
      latest: {
        completed_at: null,
        kind: 'delete_account',
        requested_at: '2026-10-10T08:00:00Z',
        status: 'processing',
      },
    })
    expect(await latestDeletionRequest(client)).toEqual({
      completedAt: null,
      kind: 'delete_account',
      requestedAt: '2026-10-10T08:00:00Z',
      status: 'processing',
    })
  })
})
