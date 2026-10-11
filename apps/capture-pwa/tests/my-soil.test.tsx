import { cleanup, render, screen } from '@testing-library/react'
import { cellToParent, latLngToCell } from 'h3-js'
import { afterEach, describe, expect, it } from 'vitest'
import { MY_SOIL_COLUMNS, mySoil } from '../src/mySoil'
import { MySoil } from '../src/MySoil'
import type { GsipClient } from '../src/supabase'

afterEach(cleanup)

const ME = 'contributor-me'
// A published resolution-8 cell, an unpublished one inside a published resolution-6 cell, and
// one in no published cell at all.
const PUBLISHED_R8 = latLngToCell(44.4759, -73.2121, 8)
const QUIET_R8 = latLngToCell(44.52, -73.15, 8)
const QUIET_R6 = cellToParent(QUIET_R8, 6)
const LONELY_R8 = latLngToCell(-1.2921, 36.8219, 8)

type Row = Record<string, unknown>

const ROWS: Row[] = [
  {
    id: 'sub-published-r8',
    contributor_id: ME,
    captured_at: '2026-10-09T15:00:00Z',
    status: 'qa_pass',
    finalized_at: '2026-10-09T15:01:00Z',
    h3_r8: PUBLISHED_R8,
    photos: [
      { shot_type: 'A', qa_status: 'pass' },
      { shot_type: 'B', qa_status: 'pass' },
      { shot_type: 'C', qa_status: 'fail' },
    ],
  },
  {
    id: 'sub-published-r6',
    contributor_id: ME,
    captured_at: '2026-10-08T15:00:00Z',
    status: 'qa_pass',
    finalized_at: '2026-10-08T15:01:00Z',
    h3_r8: QUIET_R8,
    photos: [
      { shot_type: 'A', qa_status: 'pass' },
      { shot_type: 'B', qa_status: 'pass' },
    ],
  },
  {
    id: 'sub-not-public',
    contributor_id: ME,
    captured_at: '2026-10-07T15:00:00Z',
    status: 'qa_pass',
    finalized_at: '2026-10-07T15:01:00Z',
    h3_r8: LONELY_R8,
    photos: [
      { shot_type: 'A', qa_status: 'pass' },
      { shot_type: 'B', qa_status: 'pass' },
    ],
  },
  {
    id: 'sub-checking',
    contributor_id: ME,
    captured_at: '2026-10-06T15:00:00Z',
    status: 'pending',
    finalized_at: '2026-10-06T15:01:00Z',
    h3_r8: PUBLISHED_R8,
    photos: [
      { shot_type: 'A', qa_status: 'pass' },
      { shot_type: 'B', qa_status: null },
    ],
  },
  {
    id: 'sub-failed',
    contributor_id: ME,
    captured_at: '2026-10-05T15:00:00Z',
    status: 'qa_fail',
    finalized_at: '2026-10-05T15:01:00Z',
    h3_r8: PUBLISHED_R8,
    photos: [
      { shot_type: 'A', qa_status: 'fail' },
      { shot_type: 'B', qa_status: 'pass' },
    ],
  },
  {
    // A row the server should never have returned: someone else's.
    id: 'sub-someone-else',
    contributor_id: 'contributor-other',
    captured_at: '2026-10-04T15:00:00Z',
    status: 'qa_pass',
    finalized_at: '2026-10-04T15:01:00Z',
    h3_r8: PUBLISHED_R8,
    photos: [],
  },
]

const PUBLIC_CELLS = [
  { h3_index: PUBLISHED_R8, resolution: 8 },
  { h3_index: QUIET_R6, resolution: 6 },
]

type Call = { table: string; method: string; args: unknown[] }

/** A PostgREST stand-in recording every call, answering like the real tables would. */
function fakeClient(options: { signedIn?: boolean } = {}) {
  const calls: Call[] = []
  function query(table: string) {
    const record =
      (method: string) =>
      (...args: unknown[]) => {
        calls.push({ table, method, args })
        return builder
      }
    const answer = () => {
      if (table === 'submissions') return { data: ROWS, error: null }
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
      maybeSingle: async () => ({ data: { id: ME }, error: null }),
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
    expect(entries?.map((entry) => entry.id)).toEqual([
      'sub-published-r8',
      'sub-published-r6',
      'sub-not-public',
      'sub-checking',
      'sub-failed',
    ])
  })

  it('places a passed observation in the finest published cell containing it', async () => {
    const { client } = fakeClient()
    const entries = (await mySoil(client)) ?? []
    const byId = new Map(entries.map((entry) => [entry.id, entry]))

    expect(byId.get('sub-published-r8')?.publicArea).toEqual({
      cell: PUBLISHED_R8,
      resolution: 8,
    })
    expect(byId.get('sub-published-r6')?.publicArea).toEqual({
      cell: QUIET_R6,
      resolution: 6,
    })
    expect(byId.get('sub-not-public')?.publicArea).toBeNull()
    // Only passed observations are released, so no other status names a public area.
    expect(byId.get('sub-checking')).toMatchObject({
      status: 'checking',
      publicArea: null,
      shots: { A: 'passed', B: 'pending', C: 'missing' },
    })
    expect(byId.get('sub-failed')).toMatchObject({
      status: 'failed',
      publicArea: null,
    })
  })

  it('shows dates, status, shots and public areas, never a private cell or a coordinate', async () => {
    const { client } = fakeClient()
    const { container } = render(
      <MySoil load={() => mySoil(client)} refreshKey={0} />,
    )

    expect(await screen.findAllByRole('listitem')).toHaveLength(5)
    const text = container.textContent ?? ''
    expect(text).toContain(`Public area: hexagon ${PUBLISHED_R8}`)
    expect(text).toContain(`Public area: hexagon ${QUIET_R6}`)
    expect(text).toContain('Not public yet')
    expect(text).toContain('Did not pass the quality checks')
    expect(text).toContain('A passed · B passed · C did not pass')
    // The unpublished resolution-8 cells stay private, as does anything like a coordinate.
    expect(text).not.toContain(QUIET_R8)
    expect(text).not.toContain(LONELY_R8)
    expect(text).not.toMatch(/-?\d{1,3}\.\d{3,}/)
    expect(text).not.toContain('sub-someone-else')
  })

  it('explains an empty list and a device without an account', async () => {
    const { client } = fakeClient({ signedIn: false })
    render(<MySoil load={() => mySoil(client)} refreshKey={0} />)
    expect(
      await screen.findByText(/first synced observation creates/i),
    ).toBeDefined()
    cleanup()

    render(<MySoil load={async () => []} refreshKey={0} />)
    expect(
      await screen.findByText(/appear here after they sync/i),
    ).toBeDefined()
    cleanup()

    render(
      <MySoil
        load={async () => {
          throw new Error('offline')
        }}
        refreshKey={0}
      />,
    )
    expect(await screen.findByText(/could not be loaded/i)).toBeDefined()
  })
})
