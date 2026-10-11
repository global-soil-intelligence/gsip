import { useEffect, useState } from 'react'
import { legalLinks } from './legal'
import { clearQueue } from './queue'
import {
  type DeletionKind,
  type DeletionStatus,
  type GsipClient,
  latestDeletionRequest,
  requestDeletion,
} from './supabase'

const CHOICES: Record<
  DeletionKind,
  { action: string; consequence: string; label: string; word: string }
> = {
  delete_account: {
    action: 'Delete my account…',
    consequence:
      'Your observations, photos, attribution names and account are deleted, and this device signs out. This cannot be undone.',
    label: 'Account deletion',
    word: 'DELETE',
  },
  withdraw_contributions: {
    action: 'Withdraw my contributions…',
    consequence:
      'Your observations leave every new release at once and are deleted, with their photos, within 30 days. Your account stays. This cannot be undone.',
    label: 'Withdrawal',
    word: 'WITHDRAW',
  },
}

function day(iso: string): string {
  const parsed = new Date(iso)
  return Number.isNaN(parsed.getTime()) ? iso : parsed.toLocaleDateString()
}

export function describeRequest(request: DeletionStatus): string {
  const { label } = CHOICES[request.kind]
  if (request.status === 'completed')
    return `${label} completed on ${day(request.completedAt ?? request.requestedAt)}.`
  return `${label} requested on ${day(request.requestedAt)}. Your observations are already left out of new releases; deletion completes within 30 days.`
}

/**
 * WP-6d "Your data": withdraw contributions or delete the account. Destructive requests need the
 * confirmation word typed, so a stray tap can never file one.
 */
export function YourData({
  client,
  onQueueCleared,
}: {
  client: GsipClient
  onQueueCleared: () => Promise<unknown>
}) {
  const [request, setRequest] = useState<DeletionStatus | null>(null)
  const [choice, setChoice] = useState<DeletionKind | null>(null)
  const [typed, setTyped] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const links = legalLinks()

  useEffect(() => {
    let cancelled = false
    latestDeletionRequest(client).then(
      (latest) => {
        if (!cancelled) setRequest(latest)
      },
      () => undefined,
    )
    return () => {
      cancelled = true
    }
  }, [client])

  const selected = choice ? CHOICES[choice] : null
  const confirmed =
    selected !== null && typed.trim().toUpperCase() === selected.word

  async function confirm() {
    if (!choice || !confirmed) return
    setBusy(true)
    try {
      const outcome = await requestDeletion(client, choice)
      if (outcome === 'already_open') {
        setMessage(
          'A request is already in progress. You can make another once it completes.',
        )
      } else {
        const discarded = await clearQueue()
        await onQueueCleared()
        const local = discarded
          ? ` ${discarded} observation${discarded > 1 ? 's' : ''} queued on this device ${discarded > 1 ? 'were' : 'was'} discarded.`
          : ''
        if (outcome === 'nothing_stored') {
          setMessage(
            `Nothing from this device is stored on our servers.${local}`,
          )
        } else {
          const filed: DeletionStatus = {
            completedAt: null,
            kind: choice,
            requestedAt: new Date().toISOString(),
            status: 'pending',
          }
          setRequest(filed)
          setMessage(`${describeRequest(filed)}${local}`)
        }
      }
      setChoice(null)
      setTyped('')
    } catch {
      setMessage(
        'The request could not be sent. Check your connection and try again.',
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="your-data" aria-labelledby="your-data-heading">
      <p className="step-number">Your data</p>
      <h2 id="your-data-heading">Withdraw or delete at any time</h2>
      <p>
        See the{' '}
        <a href={links.privacy} target="_blank" rel="noreferrer">
          privacy notice
        </a>{' '}
        for what we keep and why.
      </p>
      {request && (
        <p className="request-status" role="status">
          {describeRequest(request)}
        </p>
      )}
      {!selected && (
        <div className="rights-actions">
          {(Object.keys(CHOICES) as DeletionKind[]).map((kind) => (
            <button
              key={kind}
              type="button"
              className="secondary"
              onClick={() => {
                setChoice(kind)
                setTyped('')
                setMessage(null)
              }}
            >
              {CHOICES[kind].action}
            </button>
          ))}
        </div>
      )}
      {selected && (
        <div
          className="rights-confirm"
          role="group"
          aria-label="Confirm request"
        >
          <p>{selected.consequence}</p>
          <label>
            Type {selected.word} to confirm
            <input
              autoComplete="off"
              value={typed}
              onChange={(event) => setTyped(event.target.value)}
            />
          </label>
          <div className="rights-actions">
            <button
              type="button"
              disabled={!confirmed || busy}
              onClick={() => void confirm()}
            >
              Confirm {selected.label.toLowerCase()}
            </button>
            <button
              type="button"
              className="secondary"
              disabled={busy}
              onClick={() => {
                setChoice(null)
                setTyped('')
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
      {message && <p aria-live="polite">{message}</p>}
    </section>
  )
}
