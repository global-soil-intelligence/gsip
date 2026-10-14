import { useEffect, useRef, useState } from 'react'
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
      'Your observations, photos and account are deleted, your attribution names are replaced, and every device signs out. Observations still queued on your other devices will not be sent. This cannot be undone.',
    label: 'Account deletion',
    word: 'DELETE',
  },
  withdraw_contributions: {
    action: 'Withdraw my contributions…',
    consequence:
      'Every observation you have made so far, including any still queued on your other devices, is left out of releases from now on and deleted, with its photos, within 30 days. Your account stays. This cannot be undone.',
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
 * confirmation word typed, so a stray tap can never file one. Focus moves to the confirmation
 * field and back, and outcomes are announced through live regions that are always present.
 */
export function YourData({
  client,
  onQueueCleared,
  onBeforeRightsRequest,
}: {
  client: GsipClient
  onQueueCleared: () => Promise<unknown>
  onBeforeRightsRequest?: () => Promise<unknown>
}) {
  const [request, setRequest] = useState<DeletionStatus | null>(null)
  const [choice, setChoice] = useState<DeletionKind | null>(null)
  const [lastChoice, setLastChoice] = useState<DeletionKind | null>(null)
  const [typed, setTyped] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const confirmField = useRef<HTMLInputElement>(null)
  const actionButtons = useRef<
    Partial<Record<DeletionKind, HTMLButtonElement>>
  >({})
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

  useEffect(() => {
    if (choice) confirmField.current?.focus()
    else if (lastChoice) actionButtons.current[lastChoice]?.focus()
  }, [choice, lastChoice])

  const selected = choice ? CHOICES[choice] : null
  const confirmed =
    selected !== null && typed.trim().toUpperCase() === selected.word

  function close() {
    setLastChoice(choice)
    setChoice(null)
    setTyped('')
  }

  async function confirm() {
    if (!choice || !confirmed) return
    setBusy(true)
    try {
      // Fence device reminders before the rights request. A device cleanup failure must never
      // change a confirmed server request into an apparent failure or discard private content.
      try {
        await onBeforeRightsRequest?.()
      } catch {
        /* Report reminder cleanup separately. */
      }
      const outcome = await requestDeletion(client, choice)
      // Every confirmed server outcome also fulfills the person's local clear intent.
      // A failed/uncertain request throws before this point and preserves local bytes.
      const discarded = await clearQueue()
      await onQueueCleared()
      const local = discarded
        ? ` ${discarded} observation${discarded > 1 ? 's' : ''} queued on this device ${discarded > 1 ? 'were' : 'was'} discarded.`
        : ''
      if (outcome === 'already_open') {
        setMessage(
          `A request is already in progress. You can make another once it completes. Private drafts and photos on this device were cleared.${local}`,
        )
      } else {
        if (outcome === 'no_account') {
          setMessage(
            `This device has no account, so nothing from it is stored on our servers.${local}`,
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
      close()
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
      <p className="request-status" role="status" hidden={!request}>
        {request ? describeRequest(request) : ''}
      </p>
      {!selected && (
        <div className="rights-actions">
          {(Object.keys(CHOICES) as DeletionKind[]).map((kind) => (
            <button
              key={kind}
              ref={(element) => {
                if (element) actionButtons.current[kind] = element
              }}
              type="button"
              className="secondary"
              onClick={() => {
                setChoice(kind)
                setTyped('')
                setMessage('')
              }}
            >
              {CHOICES[kind].action}
            </button>
          ))}
        </div>
      )}
      {selected && choice && (
        <div
          className="rights-confirm"
          role="group"
          aria-label={`Confirm ${selected.label.toLowerCase()}`}
        >
          <p id={`rights-consequence-${choice}`}>{selected.consequence}</p>
          <label>
            Type {selected.word} to confirm
            <input
              ref={confirmField}
              autoComplete="off"
              aria-describedby={`rights-consequence-${choice}`}
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
              onClick={close}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
      <p aria-live="polite">{message}</p>
    </section>
  )
}
