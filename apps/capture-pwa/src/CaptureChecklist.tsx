import {
  type CaptureChecklistState,
  CHECKLIST_ITEMS,
  checklistProgress,
  LIGHTING_LABELS,
  type Lighting,
  PROCEDURE_LABELS,
  type Procedure,
} from './captureStandard'

/**
 * WP-COLLECT-6: an optional checklist shown before an observation is queued. It records what the
 * person says about the capture and controls nothing on the camera. It is collapsed by default,
 * and an observation queues the same with or without it.
 */
export function CaptureChecklist({
  value,
  onChange,
  disabled = false,
}: {
  value: CaptureChecklistState
  onChange: (next: CaptureChecklistState) => void
  disabled?: boolean
}) {
  const { done, total } = checklistProgress(value)
  const set = <Key extends keyof CaptureChecklistState>(
    key: Key,
    next: CaptureChecklistState[Key],
  ) => onChange({ ...value, [key]: next })
  return (
    <details className="capture-checklist">
      <summary>
        Standard capture checklist (optional) · {done} of {total} stated
        {value.shareArea ? ' · approximate area kept' : ''}
      </summary>
      <p>
        Taking every photo the same way lets photos from different phones and
        days be compared. Set these in your camera app before you take the
        photos, then say here what you did. The app cannot read or change camera
        settings, so anything you leave blank is recorded as not stated.
      </p>
      <label>
        Procedure
        <select
          name="capture-procedure"
          value={value.procedure}
          disabled={disabled}
          onChange={(event) =>
            set('procedure', event.target.value as Procedure)
          }
        >
          {(Object.keys(PROCEDURE_LABELS) as Procedure[]).map((key) => (
            <option key={key} value={key}>
              {PROCEDURE_LABELS[key]}
            </option>
          ))}
        </select>
      </label>
      <label>
        Light
        <select
          name="capture-lighting"
          value={value.lighting}
          disabled={disabled}
          onChange={(event) => set('lighting', event.target.value as Lighting)}
        >
          {(Object.keys(LIGHTING_LABELS) as Lighting[]).map((key) => (
            <option key={key} value={key}>
              {LIGHTING_LABELS[key]}
            </option>
          ))}
        </select>
      </label>
      {value.lighting === 'direct_sun' && (
        <p role="status" className="checklist-warning">
          Direct sun gives hard shadows and glare. If you can, shade the soil
          and the card together and take the photo again.
        </p>
      )}
      <ul className="checklist-items">
        {CHECKLIST_ITEMS.map(({ key, label }) => (
          <li key={key}>
            <label>
              <input
                type="checkbox"
                name={`capture-${key}`}
                checked={value[key]}
                disabled={disabled}
                onChange={(event) => set(key, event.target.checked)}
              />{' '}
              {label}
            </label>
          </li>
        ))}
      </ul>
      <label>
        Distance from lens to soil (cm)
        <input
          type="number"
          inputMode="decimal"
          name="capture-distance-cm"
          min={1}
          max={500}
          step="any"
          value={value.distanceCm}
          disabled={disabled}
          onChange={(event) => set('distanceCm', event.target.value)}
        />
      </label>
      <label>
        Width of the scene in the photo (cm), if you measured it
        <input
          type="number"
          inputMode="decimal"
          name="capture-field-of-view-cm"
          min={1}
          max={1000}
          step="any"
          value={value.fieldOfViewCm}
          disabled={disabled}
          onChange={(event) => set('fieldOfViewCm', event.target.value)}
        />
      </label>
      <label>
        Photos taken of this same sample (aim for 3 or more)
        <input
          type="number"
          inputMode="numeric"
          name="capture-replicates"
          min={1}
          max={20}
          step={1}
          value={value.replicateCount}
          disabled={disabled}
          onChange={(event) => set('replicateCount', event.target.value)}
        />
      </label>
      <label>
        <input
          type="checkbox"
          name="capture-share-area"
          checked={value.shareArea}
          disabled={disabled}
          onChange={(event) => set('shareArea', event.target.checked)}
        />{' '}
        Keep an approximate area (about 0.1 km²) with these capture details.
        Without this, they hold no place at all.
      </label>
      <p className="checklist-status" data-calibration="uncalibrated">
        Reference card: lay it flat beside the soil, in the same plane and the
        same light. This app does not detect the card yet, so every observation
        it queues is marked <strong>uncalibrated</strong>. A card is read only
        by the photo checks that run after upload. A phone photo is an RGB
        observation, not a spectrum, and these details produce no estimate of
        any soil property.
      </p>
    </details>
  )
}
