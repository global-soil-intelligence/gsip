import { cleanup, render, screen } from '@testing-library/react'
import { cellToParent, latLngToCell } from 'h3-js'
import { afterEach, describe, expect, it } from 'vitest'
import { MY_SOIL_COLUMNS, mySoil } from '../src/mySoil'
import { MySoil } from '../src/MySoilPanel'
import type { GsipClient } from '../src/supabase'

afterEach(cleanup)

const ME = 'contributor-me'
// A resolution-8 cell published inside a published resolution-6 cell; an unpublished one inside
// a published resolution-6 cell; and one in no published cell at all.
const PUBLISHED_R8 = latLngToCell(44.4759, -73.2121, 8)
const PUBLISHED_R8_PARENT = cellToParent(PUBLISHED_R8, 6)
const QUIET_R8 = latLngToCell(44.52, -73.15, 8)
const QUIET_R6 = cellToParent(QUIET_R8, 6)
const LONELY_R8 = latLngToCell(-1.2921, 36.8219, 8)

type Row = Record<string, unknown>

function row(
  id: string,
  capturedAt: string,
  status: string,
  h3R8: string,
  photos: Array<[string, string | null]>,
  extra: Row = {},
): Row {
  return {
    id,
    contributor_id: ME,
    captured_at: capturedAt,
    status,
    finalized_at: capturedAt,
    h3_r8: h3R8,
    photos: photos.map(([shot_type, qa_status]) => ({ shot_type, qa_status })),
    ...extra,
  }
}

const ROWS: Row[] = [
  row('sub-published-r8', '2026-10-09T15:00:00Z', 'qa_pass', PUBLISHED_R8, [
    ['A', 'pass'],
    ['B', 'pass'],
    ['C', 'fail'],
  ]),
  row('sub-published-r6', '2026-10-08T15:00:00Z', 'qa_pass', QUIET_R8, [
    ['A', 'pass'],
    ['B', 'pass'],
  ]),
  row('sub-not-public', '2026-10-07T15:00:00Z', 'qa_pass', LONELY_R8, [
    ['A', 'pass'],
    ['B', 'pass'],
  ]),
  row('sub-checking', '2026-10-06T15:00:00Z', 'pending', PUBLISHED_R8, [
    ['A', 'pass'],
    ['B', null],
  ]),
  row('sub-failed', '2026-10-05T15:00:00Z', 'qa_fail', PUBLISHED_R8, [
    ['A', 'fail'],
    ['B', 'pass'],
  ]),
  row('sub-flagged', '2026-10-04T15:00:00Z', 'flagged', PUBLISHED_R8, [
    ['A', 'error'],
    ['B', 'flagged'],
  ]),
  row(
    'sub-uploading',
    '2026-10-03T15:00:00Z',
    'pending',
    PUBLISHED_R8,
    [['A', null]],
    { finalized_at: null },
  ),
  // A row the server should never have returned: someone else's.
  row('sub-someone-else', '2026-10-02T15:00:00Z', 'qa_pass', PUBLISHED_R8, [], {
    contributor_id: 'contributor-other',
  }),
]

const PUBLIC_CELLS = [
  { h3_index: PUBLISHED_R8, resolution: 8 },
  { h3_index: PUBLISHED_R8_PARENT, resolution: 6 },
  { h3_index: QUIET_R6, resolution: 6 },
]

type Call = { table: string; method: string; args: unknown[] }

/** A PostgREST stand-in recording every call, answering like the real tables would. */
function fakeClient(
  options: {
    request?: Record<string, unknown> | null
    rows?: Row[]
    signedIn?: boolean
  } = {},
) {
  const calls: Call[] = []
  function query(table: string) {
    const record =
      (method: string) =>
      (...args: unknown[]) => {
        calls.push({ table, method, args })
        return builder
      }
    const answer = () => {
      if (table === 'submissions')
        return { data: options.rows ?? ROWS, error: null }
      if (table === 'h3_cells') {
        const asked = calls.find(
          (call) => call.table === 'h3_cells' && call.method === 'in',
        )?.args[1] as string[]
        return {
          data: PUBLIC_CELLS.filter((cell) => asked.includes(cell.h3_index)),
          error: null,
        }
      }
      return { data: null, error: null }
    }
    const builder = {
      select: record('select'),
      eq: record('eq'),
      in: record('in'),
      order: record('order'),
      limit: record('limit'),
      maybeSingle: async () =>
        table === 'contributors'
          ? { data: { id: ME }, error: null }
          : { data: options.request ?? null, error: null },
      then: (resolve: (value: unknown) => unknown) => resolve(answer()),
    }
    return builder
  }
  const client = {
    auth: {
      getSession: async () => ({
        data: {
          session:
            options.signedIn === false ? null : { user: { id: 'auth-me' } },
        },
        error: null,
      }),
    },
    from: (table: string) => query(table),
  }
  return { calls, client: client as unknown as GsipClient }
}

describe('My Soil (WP-APP-1)', () => {
  it('reads only the signed-in contributor’s submissions, and no location columns', async () => {
    const { calls, client } = fakeClient()
    const entries = await mySoil(client)

    const select = calls.find(
      (call) => call.table === 'submissions' && call.method === 'select',
    )
    expect(select?.args[0]).toBe(MY_SOIL_COLUMNS)
    expect(MY_SOIL_COLUMNS).not.toMatch(
      /geom|latitude|longitude|accuracy|device|metadata|evidence|h3_r6/,
    )
    expect(calls).toContainEqual({
      table: 'submissions',
      method: 'eq',
      args: ['contributor_id', ME],
    })
    expect(entries?.map((entry) => entry.id)).not.toContain('sub-someone-else')
    expect(entries).toHaveLength(ROWS.length - 1)
  })

  it('expects a passed observation in the finest published cell containing it', async () => {
    const { client } = fakeClient()
    const byId = new Map(
      ((await mySoil(client)) ?? []).map((entry) => [entry.id, entry]),
    )

    // Both its resolution-8 cell and that cell's parent are published: the finer one wins.
    expect(byId.get('sub-published-r8')?.likelyPublicArea).toEqual({
      cell: PUBLISHED_R8,
      resolution: 8,
    })
    expect(byId.get('sub-published-r6')?.likelyPublicArea).toEqual({
      cell: QUIET_R6,
      resolution: 6,
    })
    expect(byId.get('sub-not-public')?.likelyPublicArea).toBeNull()
  })

  it('follows the settlement table for statuses and shots', async () => {
    const { client } = fakeClient()
    const byId = new Map(
      ((await mySoil(client)) ?? []).map((entry) => [entry.id, entry]),
    )
    expect(byId.get('sub-published-r8')).toMatchObject({
      status: 'passed',
      shots: { A: 'passed', B: 'passed', C: 'failed' },
    })
    expect(byId.get('sub-checking')).toMatchObject({
      status: 'checking',
      likelyPublicArea: null,
      shots: { A: 'passed', B: 'pending', C: 'missing' },
    })
    expect(byId.get('sub-failed')).toMatchObject({
      status: 'failed',
      likelyPublicArea: null,
    })
    expect(byId.get('sub-flagged')).toMatchObject({
      status: 'review',
      likelyPublicArea: null,
      shots: { A: 'review', B: 'review', C: 'missing' },
    })
    expect(byId.get('sub-uploading')).toMatchObject({
      status: 'uploading',
      shots: { A: 'pending', B: 'missing', C: 'missing' },
    })
  })

  it('shows observations made before a withdrawal in progress as withdrawn, with no public area', async () => {
    const { client } = fakeClient({
      request: {
        kind: 'withdraw_contributions',
        status: 'pending',
        requested_at: '2026-10-08T20:00:00Z',
        completed_at: null,
      },
    })
    const byId = new Map(
      ((await mySoil(client)) ?? []).map((entry) => [entry.id, entry]),
    )
    expect(byId.get('sub-published-r8')).toMatchObject({
      status: 'passed',
      likelyPublicArea: { cell: PUBLISHED_R8, resolution: 8 },
    })
    expect(byId.get('sub-published-r6')).toMatchObject({
      status: 'withdrawn',
      likelyPublicArea: null,
    })

    const done = fakeClient({
      request: {
        kind: 'withdraw_contributions',
        status: 'completed',
        requested_at: '2026-10-08T20:00:00Z',
        completed_at: '2026-10-08T21:00:00Z',
      },
    })
    expect(
      ((await mySoil(done.client)) ?? []).some(
        (entry) => entry.status === 'withdrawn',
      ),
    ).toBe(false)
  })

  it('shows dates, status, shots and likely public areas, never a private cell or a coordinate', async () => {
    const { client } = fakeClient()
    const { container } = render(
      <MySoil load={() => mySoil(client)} refreshKey={0} />,
    )

    expect(await screen.findAllByRole('listitem')).toHaveLength(ROWS.length - 1)
    const text = container.textContent ?? ''
    expect(text).toContain(`Likely public area: hexagon ${PUBLISHED_R8}`)
    expect(text).toContain(`Likely public area: hexagon ${QUIET_R6}`)
    expect(text).toContain('recalculated with each nightly release')
    expect(text).toContain('Not public yet')
    expect(text).toContain('Did not pass the quality checks')
    expect(text).toContain('Held for review')
    expect(text).toContain('A passed · B passed · C did not pass')
    // The unpublished resolution-8 cells stay private, as does anything like a coordinate.
    expect(text).not.toContain(QUIET_R8)
    expect(text).not.toContain(LONELY_R8)
    expect(text).not.toMatch(/-?\d{1,3}\.\d{3,}/)
    expect(text).not.toContain('sub-someone-else')
  })

  it('explains an empty list and a device without an account, and looks again when back online', async () => {
    const { client } = fakeClient({ signedIn: false })
    render(<MySoil load={() => mySoil(client)} refreshKey={0} />)
    expect(
      await screen.findByText(/first synced observation creates/i),
    ).toBeDefined()
    cleanup()

    let calls = 0
    render(
      <MySoil
        load={async () => {
          calls += 1
          if (calls === 1) throw new Error('offline')
          return []
        }}
        refreshKey={0}
      />,
    )
    expect(await screen.findByText(/could not be loaded/i)).toBeDefined()
    window.dispatchEvent(new Event('online'))
    expect(
      await screen.findByText(/appear here after they sync/i),
    ).toBeDefined()
  })
})
