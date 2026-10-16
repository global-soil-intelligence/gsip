import { describe, expect, it } from 'vitest'
import {
  type GsipClient,
  latestDeletionRequest,
  requestDeletion,
  sendSignInLink,
} from '../src/supabase'

type Options = {
  contributor?: boolean
  insertError?: { code: string; message: string }
  latest?: Record<string, unknown> | null
  session?: boolean
  sessionError?: Error
  anonymous?: boolean
  updateError?: { code?: string; message: string }
}

function fakeClient({
  anonymous = false,
  contributor = true,
  insertError,
  latest = null,
  session = true,
  sessionError,
  updateError,
}: Options) {
  const calls: string[] = []
  const client = {
    auth: {
      getSession: async () => ({
        data: {
          session:
            session && !sessionError
              ? { user: { id: 'uid-1', is_anonymous: anonymous } }
              : null,
        },
        error: sessionError ?? null,
      }),
      signInAnonymously: async () => {
        throw new Error('a rights request must never create an account')
      },
      signInWithOtp: async () => {
        calls.push('signInWithOtp')
        return { error: null }
      },
      signOut: async (options: { scope: string }) => {
        calls.push(`signOut:${options.scope}`)
        return { error: null }
      },
      updateUser: async (attributes: { email: string }) => {
        calls.push(`updateUser:${attributes.email}`)
        return { error: updateError ?? null }
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
  it.each(['withdraw_contributions', 'delete_account'] as const)(
    'distinguishes an unused existing account for %s without creating or deleting it',
    async (kind) => {
      const { calls, client } = fakeClient({ contributor: false })
      expect(await requestDeletion(client, kind)).toBe('account_only')
      expect(calls).toEqual(['from:contributors'])
    },
  )
  it('preserves a confirmed deletion and signs out when local cleanup fails', async () => {
    const { calls, client } = fakeClient({})
    expect(
      await requestDeletion(
        client,
        'delete_account',
        () => true,
        async () => {
          throw new Error('Synthetic local cleanup failure')
        },
      ),
    ).toBe('requested_cleanup_pending')
    expect(calls).toContain('signOut:global')
    expect(
      calls.some((call) => call.startsWith('insert:deletion_requests:')),
    ).toBe(true)
  })
  it('reports no account, without signing in, when this device never had one', async () => {
    const { calls, client } = fakeClient({ session: false })
    expect(await requestDeletion(client, 'delete_account')).toBe('no_account')
    expect(await latestDeletionRequest(client)).toBeNull()
    expect(calls).toEqual([])
  })

  it('treats an unreadable session as a failure, never as "no account"', async () => {
    // Offline with an expired access token, supabase-js returns no session and an error.
    const { calls, client } = fakeClient({
      sessionError: new Error('Failed to fetch'),
    })
    await expect(
      requestDeletion(client, 'withdraw_contributions'),
    ).rejects.toThrow('Failed to fetch')
    await expect(latestDeletionRequest(client)).rejects.toThrow(
      'Failed to fetch',
    )
    expect(calls).toEqual([])
  })

  it('reports an account without contributions for a session that never became a contributor', async () => {
    const { calls, client } = fakeClient({ contributor: false })
    expect(await requestDeletion(client, 'withdraw_contributions')).toBe(
      'account_only',
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

  it('signs every device of the account out after filing an account deletion', async () => {
    const { calls, client } = fakeClient({})
    expect(await requestDeletion(client, 'delete_account')).toBe('requested')
    expect(calls.at(-1)).toBe('signOut:global')
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

describe('e-mail sign-in', () => {
  it('upgrades an anonymous account in place, so its contributions stay withdrawable', async () => {
    const { calls, client } = fakeClient({ anonymous: true })
    expect(await sendSignInLink(client, 'a@example.org', 'https://x/')).toBe(
      'confirm_sent',
    )
    expect(calls).toEqual(['updateUser:a@example.org'])
  })

  it('reports an e-mail that already has an account instead of switching silently', async () => {
    const { calls, client } = fakeClient({
      anonymous: true,
      updateError: { code: 'email_exists', message: 'exists' },
    })
    expect(await sendSignInLink(client, 'a@example.org', 'https://x/')).toBe(
      'email_in_use',
    )
    expect(calls).not.toContain('signInWithOtp')
  })

  it('switches account only when the person chooses to', async () => {
    const { calls, client } = fakeClient({ anonymous: true })
    expect(
      await sendSignInLink(client, 'a@example.org', 'https://x/', true),
    ).toBe('sent')
    expect(calls).toEqual(['signInWithOtp'])
  })

  it('sends a normal sign-in link from a signed-out or permanent session', async () => {
    const { calls, client } = fakeClient({ session: false })
    expect(await sendSignInLink(client, 'a@example.org', 'https://x/')).toBe(
      'sent',
    )
    expect(calls).toEqual(['signInWithOtp'])
  })
})
