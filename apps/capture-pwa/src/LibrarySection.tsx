import { useRef, useState } from 'react'
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
}: {
  client: GsipClient | null
  value: LibraryDraft | null
  onChange: (draft: LibraryDraft | null) => Promise<void>
}) {
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const latest = useRef(value)
  latest.current = value
  const picker = useRef(0)
  async function start() {
    setBusy(true)
    try {
      const revision = await queueRevision()
      const ownerUid = await recordOwner(client)
      const node = await libraryNodeForOwner(ownerUid, revision)
      await onChange({
        ...newLibraryDraft(node, ownerUid),
        deviceRevision: revision,
      })
    } catch {
      setMessage('The private draft could not be saved. Try again.')
    } finally {
      setBusy(false)
    }
  }
  function update(patch: Partial<LibraryDraft>) {
    if (!latest.current) return
    const next = { ...latest.current, ...patch }
    latest.current = next
    void onChange(next)
  }
  async function attach(file: File) {
    const selected = ++picker.current
    const revision = await queueRevision()
    setBusy(true)
    setMessage('')
    try {
      const attachment = await readInstrumentDeclaration(file)
      if (
        selected !== picker.current ||
        revision !== (await queueRevision()) ||
        !latest.current
      )
        return
      await onChange({ ...latest.current, ...attachment })
      setMessage(
        'Declaration saved privately. Instrument origin and physical pairing remain unverified.',
      )
    } catch {
      setMessage(
        'Choose one instrument declaration JSON file of at most 2 MB in the GSIP declaration format. Unsupported or invalid fields are refused.',
      )
    } finally {
      setBusy(false)
    }
  }
  return (
    <fieldset>
      <legend>Optional private library sample</legend>
      <p>
        Save the declared sample context with photo B. Private storage does not
        verify a spectrum, instrument, calibration or physical pair.
      </p>
      <label>
        <input
          type="checkbox"
          checked={value !== null}
          disabled={busy}
          onChange={(event) => {
            if (event.target.checked) void start()
            else {
              picker.current += 1
              void onChange(null)
            }
          }}
        />{' '}
        Add a private library sample
      </label>
      {value && (
        <>
          <div className="field-grid compact">
            <label>
              Depth top (cm)
              <input
                type="number"
                min="0"
                max="200"
                step="any"
                required
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
                value={value.depthBottom}
                onChange={(event) =>
                  update({ depthBottom: event.target.value })
                }
              />
            </label>
            <label>
              Sample condition
              <select
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
          <label>
            Instrument declaration JSON (optional)
            <input
              type="file"
              accept="application/json,.json"
              disabled={busy}
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
            library records, lab reports, CSV, PDF and original instrument files
            are unsupported. Imported files elsewhere on your device remain
            outside GSIP’s deletion control.
          </p>
          {value.instrument && (
            <button
              type="button"
              className="secondary"
              onClick={() => {
                picker.current += 1
                void onChange({
                  ...value,
                  instrument: null,
                  declarationBytes: null,
                })
              }}
            >
              Remove declaration
            </button>
          )}
        </>
      )}
      <p role="status">{message}</p>
    </fieldset>
  )
}
