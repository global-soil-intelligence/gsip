import { useEffect, useState } from 'react'
import type { MySoilEntry, MySoilStatus, PublicArea, ShotState } from './mySoil'
import type { ShotType } from './types'

const STATUS: Record<MySoilStatus, string> = {
  checking: 'Being checked',
  failed: 'Did not pass the quality checks',
  passed: 'Passed the quality checks',
  review: 'Held for review',
  uploading: 'Waiting for its photos',
  withdrawn: 'Withdrawn: left out of releases and being deleted',
}

const SHOT: Record<ShotState, string> = {
  failed: 'did not pass',
  missing: 'not taken',
  passed: 'passed',
  pending: 'being checked',
  review: 'held for review',
}

const AREA: Record<PublicArea['resolution'], string> = {
  4: 'about 1,770 km²',
  6: 'about 36 km²',
  8: 'about 0.7 km²',
}

function day(iso: string): string {
  const parsed = new Date(iso)
  return Number.isNaN(parsed.getTime())
    ? iso.slice(0, 10)
    : parsed.toLocaleDateString(undefined, {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      })
}

function publicAreaText(entry: MySoilEntry): string | null {
  if (entry.status !== 'passed') return null
  if (!entry.likelyPublicArea)
    return 'Not public yet: it appears once at least 3 contributors share its area.'
  const { cell, resolution } = entry.likelyPublicArea
  return `Likely public area: hexagon ${cell} (${AREA[resolution]}). Areas are recalculated with each nightly release.`
}

type State =
  | { kind: 'loading' }
  | { kind: 'failed' }
  | { kind: 'no_account' }
  | { kind: 'ready'; entries: MySoilEntry[] }

/**
 * WP-APP-1 "My Soil": your own observations, as the server holds them. Only the public area of
 * each is ever shown, never where it was taken.
 */
export function MySoil({
  load,
  refreshKey,
  privatePilot = false,
}: {
  load: () => Promise<MySoilEntry[] | null>
  refreshKey: number
  privatePilot?: boolean
}) {
  const [state, setState] = useState<State>({ kind: 'loading' })
  const [onlineAgain, setOnlineAgain] = useState(0)

  // Coming back online is a reason to look again.
  useEffect(() => {
    const reload = () => setOnlineAgain((count) => count + 1)
    window.addEventListener('online', reload)
    return () => window.removeEventListener('online', reload)
  }, [])

  useEffect(() => {
    let cancelled = false
    load().then(
      (entries) => {
        if (cancelled) return
        setState(
          entries === null
            ? { kind: 'no_account' }
            : { kind: 'ready', entries },
        )
      },
      () => {
        if (!cancelled) setState({ kind: 'failed' })
      },
    )
    return () => {
      cancelled = true
    }
  }, [load, refreshKey, onlineAgain])

  return (
    <section className="my-soil" aria-labelledby="my-soil-heading">
      <p className="step-number">My Soil</p>
      <h2 id="my-soil-heading">Your observations</h2>
      <div aria-live="polite">
        {state.kind === 'loading' && <p>Loading your observations…</p>}
        {state.kind === 'failed' && (
          <p>Your observations could not be loaded. Try again when online.</p>
        )}
        {state.kind === 'no_account' && (
          <p>
            {privatePilot
              ? 'Sign in to your existing invited account to see its observations. Collection never creates an account.'
              : 'Nothing yet. Your first synced observation creates this device’s private account, and it will appear here.'}
          </p>
        )}
        {state.kind === 'ready' && state.entries.length === 0 && (
          <p>Nothing yet. Observations appear here after they sync.</p>
        )}
        {state.kind === 'ready' && state.entries.length > 0 && (
          <ul className="my-soil-list">
            {state.entries.map((entry) => {
              const area = privatePilot ? null : publicAreaText(entry)
              return (
                <li key={entry.id}>
                  <strong>{day(entry.capturedAt)}</strong>
                  <span>{STATUS[entry.status]}</span>
                  <span>
                    Photos:{' '}
                    {(['A', 'B', 'C'] as ShotType[])
                      .map((shot) => `${shot} ${SHOT[entry.shots[shot]]}`)
                      .join(' · ')}
                  </span>
                  {area && <span>{area}</span>}
                </li>
              )
            })}
          </ul>
        )}
      </div>
      {privatePilot && (
        <p>
          Pilot observations remain private and unverified. They are held from
          public maps, exports and field training.
        </p>
      )}
    </section>
  )
}
