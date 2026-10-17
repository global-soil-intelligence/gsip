import { useEffect, useRef, useState } from 'react'
import {
  type LibraryDraft,
  newLibraryDraft,
  readInstrumentDeclaration,
} from './library'
import { libraryNodeForOwner, queueRevision } from './queue'
import { type GsipClient, recordOwner } from './supabase'

/** Private declarations only: this form supplies neither verification nor authority. */
export function LibrarySection({
  client,
  value,
  onChange,
  disabled = false,
  held = false,
  onPendingChange,
}: {
  client: GsipClient | null
  value: LibraryDraft | null
  onChange: (draft: LibraryDraft | null) => Promise<boolean>
  disabled?: boolean
  held?: boolean
  onPendingChange?: (pending: boolean) => void
}) {
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const latest = useRef(value)
  latest.current = value
  const picker = useRef(0)
  const pending = useRef(0)
  const mounted = useRef(true)
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
      picker.current += 1
      onPendingChange?.(false)
    }
  }, [onPendingChange])
  const revisionKnown =
    value !== null &&
    Number.isSafeInteger(value.deviceRevision) &&
    value.deviceRevision! >= 0
  const draftHeld = held || (value !== null && !revisionKnown)
  function sameDraft(original: LibraryDraft) {
    const current = latest.current
    return (
      current?.intakeId === original.intakeId &&
      current.nodeId === original.nodeId &&
      current.sampleId === original.sampleId &&
      current.submissionId === original.submissionId &&
      current.ownerUid === original.ownerUid &&
      current.deviceRevision === original.deviceRevision
    )
  }
  function begin() {
    pending.current += 1
    onPendingChange?.(true)
  }
  function finish() {
    pending.current -= 1
    if (mounted.current) {
      onPendingChange?.(pending.current > 0)
      if (pending.current === 0) setBusy(false)
    }
  }
  async function persist(next: LibraryDraft | null, selected: number) {
    begin()
    try {
      const saved = await onChange(next)
      if (mounted.current && selected === picker.current && !saved)
        setMessage(
          'The private draft could not be saved. Discard it and start again.',
        )
      return saved
    } catch {
      if (mounted.current && selected === picker.current)
        setMessage('The private draft could not be saved. Try again.')
      return false
    } finally {
      finish()
    }
  }
  async function start() {
    if (disabled) return
    const selected = ++picker.current
    const current = () =>
      mounted.current && selected === picker.current && !latest.current
    begin()
    setBusy(true)
    try {
      const revision = await queueRevision()
      if (!current()) return
      const ownerUid = await recordOwner(client)
      if (!current()) return
      const node = await libraryNodeForOwner(ownerUid, revision, current)
      if (!current()) return
      await persist(
        {
          ...newLibraryDraft(node, ownerUid),
          deviceRevision: revision,
        },
        selected,
      )
    } catch {
      if (mounted.current && selected === picker.current)
        setMessage('The private draft could not be saved. Try again.')
    } finally {
      finish()
      if (mounted.current && selected === picker.current) setBusy(false)
    }
  }
  function update(patch: Partial<LibraryDraft>) {
    if (!latest.current || draftHeld || disabled) return
    const selected = ++picker.current
    const next = { ...latest.current, ...patch }
    latest.current = next
    void persist(next, selected)
  }
  async function attach(file: File) {
    const selected = ++picker.current
    const original = latest.current
    if (!original || draftHeld || disabled) return
    const revision = original.deviceRevision
    begin()
    setBusy(true)
    setMessage('')
    try {
      const attachment = await readInstrumentDeclaration(file)
      if (
        !mounted.current ||
        selected !== picker.current ||
        !sameDraft(original)
      )
        return
      const currentRevision = await queueRevision()
      if (
        mounted.current &&
        selected === picker.current &&
        sameDraft(original) &&
        revision !== currentRevision
      )
        setMessage(
          'The private draft could not be saved. Discard it and start again.',
        )
      if (
        selected !== picker.current ||
        revision !== currentRevision ||
        !mounted.current ||
        !sameDraft(original)
      )
        return
      const saved = await persist(
        { ...latest.current!, ...attachment },
        selected,
      )
      if (
        saved &&
        mounted.current &&
        selected === picker.current &&
        sameDraft(original)
      )
        setMessage(
          'Declaration saved privately. Instrument origin and physical pairing remain unverified.',
        )
    } catch {
      if (mounted.current && selected === picker.current && sameDraft(original))
        setMessage(
          'Choose one instrument declaration JSON file of at most 2 MB in the GSIP declaration format. Unsupported or invalid fields are refused.',
        )
    } finally {
      finish()
      if (mounted.current && selected === picker.current) setBusy(false)
    }
  }
  return (
    <fieldset disabled={disabled}>
      <legend>Optional private library sample</legend>
      <p>
        Save the declared sample context with photo B. Private storage does not
        verify a spectrum, instrument, calibration or physical pair.
      </p>
      <label>
        <input
          type="checkbox"
          checked={value !== null}
          disabled={busy && !value}
          onChange={(event) => {
            if (disabled) return
            if (event.target.checked) void start()
            else {
              const selected = ++picker.current
              latest.current = null
              setMessage('')
              setBusy(true)
              void persist(null, selected).finally(() => {
                if (mounted.current && selected === picker.current)
                  setBusy(false)
              })
            }
          }}
        />{' '}
        Add a private library sample
      </label>
      {value && (
        <>
          {draftHeld && (
            <p role="status">
              This private draft has no usable original revision. Discard it and
              start again.
            </p>
          )}
          <div className="field-grid compact">
            <label>
              Depth top (cm)
              <input
                type="number"
                min="0"
                max="200"
                step="any"
                required
                disabled={draftHeld}
                value={value.depthTop}
                onChange={(event) => update({ depthTop: event.target.value })}
              />
            </label>
            <label>
              Depth bottom (cm)
              <input
                type="number"
                min="0"
                max="200"
                step="any"
                required
                disabled={draftHeld}
                value={value.depthBottom}
                onChange={(event) =>
                  update({ depthBottom: event.target.value })
                }
              />
            </label>
            <label>
              Sample condition
              <select
                disabled={draftHeld}
                value={value.condition}
                onChange={(event) =>
                  update({
                    condition: event.target.value as LibraryDraft['condition'],
                  })
                }
              >
                <option value="unknown">Unknown</option>
                <option value="dry">Dry</option>
                <option value="moist">Moist</option>
                <option value="wet">Wet</option>
              </select>
            </label>
          </div>
          <p>
            Enter the sampled depth bounds yourself: 0 ≤ top &lt; bottom ≤ 200
            cm. Leave condition unknown when it was not recorded.
          </p>
          <details>
            <summary>Advanced: instrument declaration (optional)</summary>
            <label>
              Instrument declaration JSON (optional)
              <input
                type="file"
                accept="application/json,.json"
                disabled={busy || draftHeld}
                onChange={(event) => {
                  const file = event.currentTarget.files?.[0]
                  event.currentTarget.value = ''
                  if (file) void attach(file)
                }}
              />
            </label>
            <p>
              Accepts only measurement_id and an instrument_reflectance
              measurement with declared source hash, instrument/calibration IDs
              and aligned wavelength, reflectance and uncertainty arrays. Local
              library records, lab reports, CSV, PDF and original instrument
              files are unsupported. Imported files elsewhere on your device
              remain outside GSIP’s deletion control.
            </p>
          </details>
          {value.instrument && (
            <>
              <p>
                Instrument declaration attached privately. Origin, calibration
                and physical pairing remain unverified.
              </p>
              <button
                type="button"
                className="secondary"
                disabled={draftHeld}
                onClick={() => {
                  const selected = ++picker.current
                  const next = {
                    ...value,
                    instrument: null,
                    declarationBytes: null,
                  }
                  latest.current = next
                  void persist(next, selected)
                }}
              >
                Remove declaration
              </button>
            </>
          )}
        </>
      )}
      <p role="status">{message}</p>
    </fieldset>
  )
}
