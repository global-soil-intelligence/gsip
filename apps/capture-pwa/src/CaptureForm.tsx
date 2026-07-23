import { useEffect, useState } from 'react'
import { HexPreview } from './HexPreview'
import { fuzzLocation } from './geo'
import { isNative, locateDevice, nativePhoto } from './platform'
import type { QueueRecord, QueuedPhoto, ShotType } from './types'

export function coarseDeviceModel(): string {
  return (
    navigator.userAgent.match(
      /Android|iPhone|iPad|Macintosh|Windows|Linux/i,
    )?.[0] ?? 'unknown device'
  )
}
const shots: Array<{ id: ShotType; title: string; help: string }> = [
  {
    id: 'A',
    title: 'A · Context / 30 cm',
    help: 'Undisturbed ground, with the reference card in frame.',
  },
  {
    id: 'B',
    title: 'B · Fresh face / 15 cm',
    help: 'Expose a fresh soil face and photograph it close up.',
  },
  {
    id: 'C',
    title: 'C · Moist texture',
    help: 'Optional: a moist soil ball or ribbon.',
  },
]
function PhotoPreview({ photo }: { photo: QueuedPhoto }) {
  const [url, setUrl] = useState('')
  useEffect(() => {
    const next = URL.createObjectURL(
      new Blob([new Uint8Array(photo.bytes)], { type: 'image/jpeg' }),
    )
    setUrl(next)
    return () => URL.revokeObjectURL(next)
  }, [photo])
  return (
    <img
      className="photo-preview"
      src={url}
      alt={`Selected soil photo ${photo.shotType}`}
    />
  )
}

export function CaptureForm({
  initial,
  onSave,
  saving,
}: {
  initial?: QueueRecord
  onSave: (record: QueueRecord) => Promise<void>
  saving: boolean
}) {
  const [id] = useState(() => initial?.submissionId ?? crypto.randomUUID())
  const [grantId] = useState(() => initial?.grantId ?? crypto.randomUUID())
  const [selected, setSelected] = useState<QueuedPhoto[]>(initial?.photos ?? [])
  const [latitude, setLatitude] = useState(
    initial && Number.isFinite(initial.latitude)
      ? String(initial.latitude)
      : '',
  )
  const [longitude, setLongitude] = useState(
    initial && Number.isFinite(initial.longitude)
      ? String(initial.longitude)
      : '',
  )
  const [accuracy, setAccuracy] = useState<number | null>(
    initial?.accuracyM ?? null,
  )
  const [land, setLand] = useState(initial?.landCover ?? '')
  const [moisture, setMoisture] = useState(initial?.surfaceCondition ?? '')
  const [disturbed, setDisturbed] = useState(initial?.disturbed ?? false)
  const [attribution, setAttribution] = useState(
    initial?.attributionName ?? 'Anonymous soil contributor',
  )
  const [consent, setConsent] = useState(false)
  const [error, setError] = useState('')
  const [locating, setLocating] = useState(false)
  const [reading, setReading] = useState(false)
  const validLocation =
    latitude.trim() !== '' &&
    longitude.trim() !== '' &&
    Number.isFinite(Number(latitude)) &&
    Number.isFinite(Number(longitude)) &&
    Math.abs(Number(latitude)) <= 90 &&
    Math.abs(Number(longitude)) <= 180
  const publicCell = validLocation
    ? fuzzLocation(Number(latitude), Number(longitude)).h3R8
    : null
  async function selectPhoto(shotType: ShotType, file?: File) {
    if (!file) return
    setError('')
    setReading(true)
    try {
      if (file.type !== 'image/jpeg')
        throw new Error(
          'Choose JPEG photos. On your phone, use the camera to capture a compatible image.',
        )
      if (file.size > 12 * 1024 * 1024)
        throw new Error(
          'This photo is larger than 12 MB. Choose a smaller JPEG or take a new photo.',
        )
      const bytes = new Uint8Array(await file.arrayBuffer())
      if (bytes[0] !== 0xff || bytes[1] !== 0xd8)
        throw new Error('This file is not a valid JPEG photo.')
      setSelected((current) =>
        [
          ...current.filter((p) => p.shotType !== shotType),
          {
            bytes,
            mimeType: 'image/jpeg',
            objectId: crypto.randomUUID(),
            shotType,
          },
        ].sort((a, b) => a.shotType.localeCompare(b.shotType)),
      )
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : 'Could not read this photo. Please try again.',
      )
    } finally {
      setReading(false)
    }
  }
  async function locate() {
    setLocating(true)
    setError('')
    try {
      const p = await locateDevice()
      setLatitude(p.latitude.toFixed(6))
      setLongitude(p.longitude.toFixed(6))
      setAccuracy(Math.round(p.accuracy))
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : 'Location unavailable. Enter coordinates below.',
      )
    } finally {
      setLocating(false)
    }
  }
  async function save(draft: boolean) {
    setError('')
    if (
      !draft &&
      (!validLocation ||
        !selected.some((p) => p.shotType === 'A') ||
        !selected.some((p) => p.shotType === 'B') ||
        !land ||
        !moisture ||
        !consent)
    ) {
      setError(
        'Add both required photos, a valid location, field conditions, and your consent.',
      )
      return
    }
    // Drafts may be incomplete. Blank coordinates use NaN locally and are never synced.
    const record: QueueRecord = {
      ...initial,
      submissionId: id,
      grantId,
      draft,
      photos: selected,
      latitude: validLocation ? Number(latitude) : NaN,
      longitude: validLocation ? Number(longitude) : NaN,
      accuracyM: accuracy,
      landCover: land,
      surfaceCondition: moisture,
      disturbed,
      attributionName: attribution.trim() || 'Anonymous soil contributor',
      deviceModel: coarseDeviceModel(),
      capturedAt: new Date().toISOString(),
      queuedAt: new Date().toISOString(),
      termsVersion: '2026-07-22-v1',
    }
    try {
      await onSave(record)
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : 'Could not save. Your photos remain here; please retry.',
      )
    }
  }
  return (
    <form
      className="capture-form"
      onSubmit={(event) => {
        event.preventDefault()
        void save(false)
      }}
    >
      <section className="field-card">
        <div className="section-heading">
          <span className="step">01</span>
          <div>
            <h2>Look closer.</h2>
            <p>
              Two photos tell the story. Use even daylight and keep the card
              visible.
            </p>
          </div>
        </div>
        <div className="photo-grid">
          {shots.map((shot) => {
            const photo = selected.find((p) => p.shotType === shot.id)
            return (
              <div className="photo-field" key={shot.id}>
                {photo ? (
                  <PhotoPreview photo={photo} />
                ) : (
                  <div className="photo-placeholder" aria-hidden="true">
                    <svg viewBox="0 0 80 64">
                      <path d="M10 20h15l6-9h18l6 9h15v36H10z" />
                      <circle cx="40" cy="37" r="12" />
                    </svg>
                    <span>{shot.id}</span>
                  </div>
                )}
                <label>
                  <strong>{shot.title}</strong>
                  <small>{shot.help}</small>
                  <input
                    name={`shot-${shot.id.toLowerCase()}`}
                    aria-label={shot.title}
                    type="file"
                    accept="image/jpeg"
                    capture="environment"
                    disabled={reading || saving}
                    onChange={(e) =>
                      void selectPhoto(shot.id, e.target.files?.[0])
                    }
                  />
                </label>
                {isNative() && (
                  <button
                    type="button"
                    className="secondary"
                    disabled={reading || saving}
                    onClick={() =>
                      void nativePhoto()
                        .then((file) => selectPhoto(shot.id, file))
                        .catch(() =>
                          setError(
                            'Camera closed or unavailable. You can choose a JPEG instead.',
                          ),
                        )
                    }
                  >
                    Open camera for {shot.id}
                  </button>
                )}
                {photo && (
                  <button
                    type="button"
                    className="text-button"
                    onClick={() =>
                      setSelected((current) =>
                        current.filter((p) => p.shotType !== shot.id),
                      )
                    }
                  >
                    Remove photo {shot.id}
                  </button>
                )}
              </div>
            )
          })}
        </div>
        <p className="hint">
          No reference card? You can still contribute. Your photos will be
          marked uncalibrated.
        </p>
      </section>
      <section className="field-card">
        <div className="section-heading">
          <span className="step">02</span>
          <div>
            <h2>A little field context.</h2>
            <p>Describe what you see, then add a private location.</p>
          </div>
        </div>
        <div className="field-grid">
          <label>
            Land cover
            <select value={land} onChange={(e) => setLand(e.target.value)}>
              <option value="">Choose one</option>
              {[
                'cropland',
                'grassland',
                'forest',
                'shrubland',
                'wetland',
                'urban',
                'bare',
              ].map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </label>
          <label>
            Surface condition
            <select
              value={moisture}
              onChange={(e) => setMoisture(e.target.value)}
            >
              <option value="">Choose one</option>
              {['dry', 'moist', 'wet'].map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </label>
          <label>
            Recently disturbed?
            <select
              value={disturbed ? 'yes' : 'no'}
              onChange={(e) => setDisturbed(e.target.value === 'yes')}
            >
              <option value="no">No</option>
              <option value="yes">Yes</option>
            </select>
          </label>
        </div>
        <button
          className="secondary"
          type="button"
          disabled={locating}
          onClick={() => void locate()}
        >
          {locating ? 'Locating…' : 'Use my current location'}
        </button>
        <div className="field-grid coordinates">
          <label>
            Latitude
            <input
              type="number"
              min="-90"
              max="90"
              step="any"
              inputMode="decimal"
              value={latitude}
              onChange={(e) => {
                setLatitude(e.target.value)
                setAccuracy(null)
              }}
            />
          </label>
          <label>
            Longitude
            <input
              type="number"
              min="-180"
              max="180"
              step="any"
              inputMode="decimal"
              value={longitude}
              onChange={(e) => {
                setLongitude(e.target.value)
                setAccuracy(null)
              }}
            />
          </label>
        </div>
        <p className="hint">
          {accuracy !== null ? `Location accuracy: ±${accuracy} m. ` : ''}Exact
          coordinates stay private. Only the approximate cell becomes public.
        </p>
        {publicCell && <HexPreview cell={publicCell} />}
      </section>
      <section className="field-card">
        <div className="section-heading">
          <span className="step">03</span>
          <div>
            <h2>Make it part of something bigger.</h2>
            <p>Review your photos and choose how to be credited.</p>
          </div>
        </div>
        <label>
          Public attribution name
          <input
            maxLength={80}
            value={attribution}
            onChange={(e) => setAttribution(e.target.value)}
          />
        </label>
        <label className="terms">
          <input
            type="checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
          />
          <span>
            I own these photos and agree to publish approved, sanitized photos
            under CC BY-SA 4.0 and structured data under ODbL 1.0. My exact
            location stays private. My acceptance is recorded for this
            contribution.
          </span>
        </label>
        <div className="action-row">
          <button type="submit" disabled={saving || reading}>
            {saving ? 'Saving…' : 'Queue observation securely'}
          </button>
          <button
            type="button"
            className="secondary"
            disabled={saving || reading}
            onClick={() => void save(true)}
          >
            Save draft on this device
          </button>
        </div>
        <p className="hint">
          Offline? Keep GSIP open when you reconnect, or reopen it to resume
          uploading.
        </p>
      </section>
      {error && (
        <p className="notice error" role="alert">
          {error}
        </p>
      )}
    </form>
  )
}
