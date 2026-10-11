import { describe, expect, it } from 'vitest'
import { drainQueue } from '../src/sync'
import {
  fetchServiceState,
  type GsipClient,
  photoStoragePath,
  submitQueued,
} from '../src/supabase'
import type { QueueRecord } from '../src/types'

type QueryResult = { data: unknown; error: Error | null }

type FakeState = {
  failFinalize: boolean
  failNextUpload: boolean
  grantPayloads: Array<Record<string, unknown>>
  grants: Set<string>
  log: string[]
  photos: Set<string>
  submissions: Map<string, Record<string, unknown>>
  uploads: Set<string>
}

class FakeQuery implements PromiseLike<QueryResult> {
  private filters = new Map<string, unknown>()
  private result: QueryResult = { data: null, error: null }

  constructor(
    private readonly state: FakeState,
    private readonly table: string,
  ) {}

  select(): this {
    return this
  }

  eq(column: string, value: unknown): this {
    this.filters.set(column, value)
    return this
  }

  async maybeSingle(): Promise<QueryResult> {
    if (this.table === 'contributors') {
      return { data: { id: 'contributor-id' }, error: null }
    }
    if (this.table === 'contribution_grants') {
      const id = String(this.filters.get('id'))
      return { data: this.state.grants.has(id) ? { id } : null, error: null }
    }
    if (this.table === 'submissions') {
      const id = String(this.filters.get('id'))
      return { data: this.state.submissions.get(id) ?? null, error: null }
    }
    if (this.table === 'photos') {
      const key = `${this.filters.get('submission_id')}:${this.filters.get('shot_type')}`
      return {
        data: this.state.photos.has(key) ? { id: key } : null,
        error: null,
      }
    }
    return { data: null, error: null }
  }

  insert(payload: Record<string, unknown>): this {
    this.state.log.push(`insert:${this.table}`)
    if (this.table === 'contribution_grants') {
      this.state.grants.add(String(payload.id))
      this.state.grantPayloads.push(payload)
    }
    if (this.table === 'submissions') {
      this.state.submissions.set(String(payload.id), payload)
    }
    if (this.table === 'photos') {
      this.state.photos.add(`${payload.submission_id}:${payload.shot_type}`)
    }
    this.result = { data: null, error: null }
    return this
  }

  async single(): Promise<QueryResult> {
    return { data: { id: 'contributor-id' }, error: null }
  }

  then<TResult1 = QueryResult, TResult2 = never>(
    onfulfilled?:
      ((value: QueryResult) => TResult1 | PromiseLike<TResult1>) | null,
    onrejected?: ((reason: unknown) => TResult2 | PromiseLike<TResult2>) | null,
  ): Promise<TResult1 | TResult2> {
    return Promise.resolve(this.result).then(onfulfilled, onrejected)
  }
}

function fakeClient(state: FakeState): GsipClient {
  return {
    auth: {
      getSession: async () => ({
        data: { session: { user: { id: 'user-id' } } },
        error: null,
      }),
    },
    from: (table: string) => new FakeQuery(state, table),
    rpc: async (name: string, args: Record<string, unknown>) => {
      state.log.push(`rpc:${name}`)
      if (
        name === 'finalize_submission' &&
        (state.failFinalize ||
          !state.submissions.has(String(args.p_submission_id)))
      )
        return { data: null, error: new Error('submission not found') }
      return { data: '2026-07-23T00:05:00Z', error: null }
    },
    functions: {
      invoke: async () => {
        state.log.push('invoke:prior-attach')
        return { data: {}, error: null }
      },
    },
    storage: {
      from: () => ({
        upload: async (path: string) => {
          state.log.push('upload:photo')
          if (state.failNextUpload) {
            state.failNextUpload = false
            return {
              data: null,
              error: { message: 'temporary upload failure', statusCode: 503 },
            }
          }
          state.uploads.add(path)
          return { data: { path }, error: null }
        },
      }),
    },
  } as unknown as GsipClient
}

function queuedRecord(): QueueRecord {
  return {
    acceptedAt: '2026-07-23T00:10:00Z',
    accuracyM: 8,
    attributionName: 'Field contributor',
    capturedAt: '2026-07-01T08:00:00Z',
    deviceModel: 'Macintosh',
    disturbed: false,
    grantId: 'grant-id',
    landCover: 'cropland',
    latitude: 40.446,
    longitude: -79.982,
    photos: [
      {
        bytes: new TextEncoder().encode('jpeg'),
        mimeType: 'image/jpeg',
        objectId: 'photo-a',
        shotType: 'A',
      },
      {
        bytes: new TextEncoder().encode('jpeg'),
        mimeType: 'image/jpeg',
        objectId: 'photo-b',
        shotType: 'B',
      },
    ],
    queuedAt: '2026-07-23T00:00:00Z',
    submissionId: 'submission-id',
    surfaceCondition: 'moist',
    termsVersion: '2026-07-22-v1',
  }
}

function fakeState(): FakeState {
  return {
    failFinalize: false,
    failNextUpload: false,
    grantPayloads: [],
    grants: new Set(),
    log: [],
    photos: new Set(),
    submissions: new Map(),
    uploads: new Set(),
  }
}

describe('hosted submission paths', () => {
  it('keeps uploads beneath the authenticated owner prefix', () => {
    const record = {
      photos: [{ objectId: 'photo-id', shotType: 'B' }],
      submissionId: 'submission-id',
    } as QueueRecord

    expect(photoStoragePath('user-id', record, record.photos[0])).toBe(
      'user-id/submission-id/B/photo-id.jpg',
    )
  })

  it('creates the immutable grant before the exact submission and uploads', async () => {
    const state = fakeState()
    const record = queuedRecord()
    await submitQueued(fakeClient(state), record)

    expect(state.log).toEqual([
      'insert:contribution_grants',
      'insert:submissions',
      'upload:photo',
      'insert:photos',
      'upload:photo',
      'insert:photos',
      'rpc:finalize_submission',
      'invoke:prior-attach',
    ])
    // The grant records when the terms were accepted, never the photo's timestamp.
    expect(state.grantPayloads[0]).toMatchObject({
      accepted_at: '2026-07-23T00:10:00Z',
    })
    expect(state.submissions.get(record.submissionId)).toMatchObject({
      device_model: 'Macintosh',
      gps_accuracy_m: 8,
      id: record.submissionId,
      status: 'pending',
    })
  })

  it('resumes idempotently after a photo upload fails mid-sequence', async () => {
    const state = fakeState()
    state.failNextUpload = true
    const record = queuedRecord()
    const client = fakeClient(state)

    await expect(submitQueued(client, record)).rejects.toMatchObject({
      statusCode: 503,
    })
    await submitQueued(client, record)

    expect(
      state.log.filter((event) => event === 'insert:submissions'),
    ).toHaveLength(1)
    expect(
      state.log.filter((event) => event === 'insert:contribution_grants'),
    ).toHaveLength(1)
    expect(state.photos).toEqual(
      new Set(['submission-id:A', 'submission-id:B']),
    )
  })

  it('falls back to the queue time for records queued by older builds', async () => {
    const state = fakeState()
    const record = queuedRecord()
    delete record.acceptedAt
    await submitQueued(fakeClient(state), record)
    expect(state.grantPayloads[0]).toMatchObject({
      accepted_at: record.queuedAt,
    })
  })

  it('keeps the record queued when finalize fails', async () => {
    const state = fakeState()
    state.failFinalize = true
    await expect(
      submitQueued(fakeClient(state), queuedRecord()),
    ).rejects.toThrow('submission not found')
    expect(state.log).not.toContain('invoke:prior-attach')
  })

  it('removes a queue record only after the complete hosted path succeeds', async () => {
    const state = fakeState()
    state.failNextUpload = true
    const record = queuedRecord()
    const client = fakeClient(state)
    const removed: string[] = []
    let storedRecord = record
    let now = Date.parse('2026-07-23T00:00:00Z')
    const store = {
      list: async () => [storedRecord],
      put: async (next: QueueRecord) => {
        storedRecord = next
      },
      remove: async (id: string) => {
        removed.push(id)
      },
    }

    expect(
      await drainQueue(
        store,
        (item) => submitQueued(client, item),
        () => now,
      ),
    ).toMatchObject({
      failed: 1,
      synced: 0,
    })
    expect(removed).toEqual([])
    now = Date.parse(storedRecord.nextRetryAt ?? '')
    expect(
      await drainQueue(
        store,
        (item) => submitQueued(client, item),
        () => now,
      ),
    ).toMatchObject({
      failed: 0,
      synced: 1,
    })
    expect(removed).toEqual(['submission-id'])
  })
})

describe('capture gate state', () => {
  function stateClient(result: { data: unknown; error: unknown } | Error) {
    return {
      from: () => ({
        select: () => ({
          maybeSingle: async () => {
            if (result instanceof Error) throw result
            return result
          },
        }),
      }),
    } as unknown as GsipClient
  }

  it('maps the database switch to open or closed', async () => {
    expect(
      await fetchServiceState(
        stateClient({ data: { capture_open: true }, error: null }),
      ),
    ).toBe('open')
    expect(
      await fetchServiceState(
        stateClient({ data: { capture_open: false }, error: null }),
      ),
    ).toBe('closed')
  })

  it('treats unreadable state as unknown, never as closed', async () => {
    expect(
      await fetchServiceState(stateClient({ data: null, error: null })),
    ).toBe('unknown')
    expect(
      await fetchServiceState(
        stateClient({ data: null, error: { message: 'offline' } }),
      ),
    ).toBe('unknown')
    expect(await fetchServiceState(stateClient(new Error('network')))).toBe(
      'unknown',
    )
  })
})
