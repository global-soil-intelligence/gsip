import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { fuzzLocation } from './geo'
import { HexPreview } from './HexPreview'
import { enqueue, indexedDbQueue, queued } from './queue'
import { drainQueue } from './sync'
import { createGsipClient, isServiceConfigured, submitQueued } from './supabase'
import type { QueueRecord, ShotType } from './types'

const TERMS_VERSION = '2026-07-22-v1'
const LAND_COVERS = [
  'cropland',
  'grassland',
  'forest',
  'shrubland',
  'wetland',
  'urban',
  'bare',
]

function PhotoField({
  label,
  name,
  optional = false,
}: {
  label: string
  name: string
  optional?: boolean
}) {
  return (
    <label className="photo-field">
      <span>{label}</span>
      <small>{optional ? 'Optional confidence boost' : 'Required'}</small>
      <div className="camera-guide" aria-hidden="true">
        <span>Keep card + soil inside the guide</span>
      </div>
      <input
        name={name}
        type="file"
        accept="image/jpeg,image/*"
        capture="environment"
        required={!optional}
      />
    </label>
  )
}

async function photos(form: FormData): Promise<QueueRecord['photos']> {
  const readBytes = (file: File) =>
    new Promise<Uint8Array>((resolve, reject) => {
      const reader = new FileReader()
      reader.onerror = () =>
        reject(
          reader.error ?? new Error('The selected photo could not be read.'),
        )
      reader.onload = () =>
        resolve(new Uint8Array(reader.result as ArrayBuffer))
      reader.readAsArrayBuffer(file)
    })
  const captured = await Promise.all(
    (['A', 'B', 'C'] as ShotType[]).map(async (shotType) => {
      const file = form.get(`shot-${shotType.toLowerCase()}`)
      return file instanceof File && file.size
        ? {
            bytes: await readBytes(file),
            mimeType: file.type || 'image/jpeg',
            objectId: crypto.randomUUID(),
            shotType,
          }
        : null
    }),
  )
  return captured.filter(
    (photo): photo is NonNullable<typeof photo> => photo !== null,
  )
}

export function App() {
  const formRef = useRef<HTMLFormElement>(null)
  const client = useMemo(
    () => (isServiceConfigured() ? createGsipClient() : null),
    [],
  )
  const [accuracy, setAccuracy] = useState<number | null>(null)
  const [latitude, setLatitude] = useState('')
  const [longitude, setLongitude] = useState('')
  const [queueCount, setQueueCount] = useState(0)
  const [status, setStatus] = useState('Ready for your first observation.')
  const [publicCell, setPublicCell] = useState<string | null>(null)
  const [email, setEmail] = useState('')

  const refreshQueueCount = useCallback(
    async () => setQueueCount((await queued()).length),
    [],
  )
  const sync = useCallback(async () => {
    if (!client || !navigator.onLine) return
    setStatus('Securely syncing queued observations…')
    const result = await drainQueue(indexedDbQueue, (record) =>
      submitQueued(client, record),
    )
    await refreshQueueCount()
    if (result.synced)
      setStatus(
        `${result.synced} observation${result.synced > 1 ? 's' : ''} synced.`,
      )
    if (result.failed)
      setStatus(
        'Sync paused. Your observation remains safely queued on this device.',
      )
  }, [client, refreshQueueCount])

  useEffect(() => {
    void refreshQueueCount()
    const onOnline = () => void sync()
    window.addEventListener('online', onOnline)
    return () => window.removeEventListener('online', onOnline)
  }, [refreshQueueCount, sync])

  function locate() {
    if (!navigator.geolocation) {
      setStatus(
        'Location is unavailable. Enter a latitude and longitude below.',
      )
      return
    }
    setStatus('Requesting location permission…')
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLatitude(position.coords.latitude.toFixed(6))
        setLongitude(position.coords.longitude.toFixed(6))
        setAccuracy(Math.round(position.coords.accuracy))
        setStatus('Location captured. Only the fuzzed H3 cell becomes public.')
      },
      () =>
        setStatus('Location was not shared. Use the manual fallback below.'),
      { enableHighAccuracy: true, maximumAge: 30_000, timeout: 15_000 },
    )
  }

  async function sendMagicLink() {
    if (!client || !email) return
    const { error } = await client.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: window.location.href.split('#')[0] },
    })
    setStatus(
      error
        ? 'Magic link could not be sent. Try again.'
        : 'Check your email for the secure sign-in link.',
    )
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const numericLatitude = Number(latitude)
    const numericLongitude = Number(longitude)
    if (
      !Number.isFinite(numericLatitude) ||
      !Number.isFinite(numericLongitude)
    ) {
      setStatus('Add a valid location before continuing.')
      return
    }
    const record: QueueRecord = {
      accuracyM: accuracy,
      attributionName: String(
        form.get('attribution') || 'Anonymous soil contributor',
      ),
      capturedAt: new Date().toISOString(),
      disturbed: form.get('disturbed') === 'yes',
      grantId: crypto.randomUUID(),
      landCover: String(form.get('land-cover')),
      latitude: numericLatitude,
      longitude: numericLongitude,
      photos: await photos(form),
      queuedAt: new Date().toISOString(),
      submissionId: crypto.randomUUID(),
      surfaceCondition: String(form.get('surface-condition')),
      termsVersion: TERMS_VERSION,
    }
    await enqueue(record)
    setPublicCell(fuzzLocation(numericLatitude, numericLongitude).h3R8)
    formRef.current?.reset()
    setLatitude('')
    setLongitude('')
    setAccuracy(null)
    await refreshQueueCount()
    if (navigator.onLine && client) await sync()
    else
      setStatus(
        'Saved offline. It will sync automatically when this device reconnects.',
      )
  }

  return (
    <div className="app-shell">
      <header>
        <a className="brand" href="../map/" aria-label="GSIP public map">
          <span className="brand-mark">G</span>
          <span>Global Soil Intelligence</span>
        </a>
        <div className="queue-pill" aria-live="polite">
          <span className={navigator.onLine ? 'online' : 'offline'} />
          {queueCount
            ? `${queueCount} queued`
            : navigator.onLine
              ? 'Online'
              : 'Offline ready'}
        </div>
      </header>

      <main>
        <section className="hero">
          <p className="eyebrow">Three photos. One living planet.</p>
          <h1>Help map the ground beneath us.</h1>
          <p className="lede">
            Photograph soil with the free GSIP card. Your precise location stays
            private; the public map sees only a broad hexagonal cell.
          </p>
          <a
            className="card-link"
            href="../reference-card/gsip-reference-card-v1-color.pdf"
            download
          >
            Download the printable A6 card ↗
          </a>
        </section>

        <aside className="privacy-note">
          <strong>Privacy by design</strong>
          <span>
            Precise coordinates and original photos remain private. Public data
            is H3-fuzzed.
          </span>
        </aside>

        <section className="signin-card" aria-labelledby="signin-heading">
          <div>
            <p className="step-number">Optional account</p>
            <h2 id="signin-heading">Keep contributing privately</h2>
            <p>
              Submit anonymously now, or send yourself a magic link to return to
              your history.
            </p>
          </div>
          <div className="magic-link">
            <label>
              Email
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
              />
            </label>
            <button
              type="button"
              className="secondary"
              disabled={!client || !email}
              onClick={() => void sendMagicLink()}
            >
              Send magic link
            </button>
          </div>
        </section>

        <form ref={formRef} onSubmit={(event) => void submit(event)}>
          <fieldset>
            <legend>
              <span>01</span> Capture the soil
            </legend>
            <p>
              Use even daylight. Keep the whole reference card visible and avoid
              glare.
            </p>
            <div className="photo-grid">
              <PhotoField name="shot-a" label="A · Context / 30 cm" />
              <PhotoField name="shot-b" label="B · Fresh face / 15 cm" />
              <PhotoField name="shot-c" label="C · Moist texture" optional />
            </div>
          </fieldset>

          <fieldset>
            <legend>
              <span>02</span> Describe the place
            </legend>
            <div className="field-grid">
              <label>
                Land cover
                <select name="land-cover" required defaultValue="">
                  <option value="" disabled>
                    Choose one
                  </option>
                  {LAND_COVERS.map((cover) => (
                    <option key={cover}>{cover}</option>
                  ))}
                </select>
              </label>
              <label>
                Surface condition
                <select name="surface-condition" required defaultValue="">
                  <option value="" disabled>
                    Choose one
                  </option>
                  <option>dry</option>
                  <option>moist</option>
                  <option>wet</option>
                </select>
              </label>
              <label>
                Recently disturbed?
                <select name="disturbed" required defaultValue="no">
                  <option value="no">No</option>
                  <option value="yes">Yes</option>
                </select>
              </label>
            </div>
          </fieldset>

          <fieldset>
            <legend>
              <span>03</span> Add a private location
            </legend>
            <p>
              We store the exact point privately for scientific processing. Only
              its H3 resolution-8 cell is public.
            </p>
            <button type="button" className="location-button" onClick={locate}>
              Use my current location
            </button>
            <div className="field-grid compact">
              <label>
                Latitude
                <input
                  aria-label="Latitude"
                  inputMode="decimal"
                  min="-90"
                  max="90"
                  type="number"
                  step="any"
                  required
                  value={latitude}
                  onChange={(event) => setLatitude(event.target.value)}
                />
              </label>
              <label>
                Longitude
                <input
                  aria-label="Longitude"
                  inputMode="decimal"
                  min="-180"
                  max="180"
                  type="number"
                  step="any"
                  required
                  value={longitude}
                  onChange={(event) => setLongitude(event.target.value)}
                />
              </label>
              <div className="accuracy">
                {accuracy
                  ? `Accuracy ±${accuracy} m`
                  : 'Manual pin fallback available'}
              </div>
            </div>
          </fieldset>

          <fieldset>
            <legend>
              <span>04</span> Grant & submit
            </legend>
            <label>
              Public photo attribution name or pseudonym
              <input
                name="attribution"
                minLength={1}
                maxLength={80}
                required
                defaultValue="Anonymous soil contributor"
              />
            </label>
            <label className="terms">
              <input type="checkbox" required />{' '}
              <span>
                I own these photos and grant GSIP permission to include
                structured contribution data in the ODbL 1.0 database and
                publish sanitized photos under CC BY-SA 4.0. I understand this
                is an immutable acceptance snapshot for this submission.
              </span>
            </label>
            <button className="submit-button" type="submit">
              Queue observation securely
            </button>
            {!client && (
              <p className="config-warning">
                Preview mode: deployment configuration is not available, so
                submissions remain on this device.
              </p>
            )}
          </fieldset>
        </form>

        <section className="status-card" aria-live="polite">
          <div>
            <p className="step-number">Status</p>
            <h2>{status}</h2>
          </div>
          {publicCell && <HexPreview cell={publicCell} />}
        </section>
      </main>
      <footer>
        Open science · Privacy-safe by default · Estimates include uncertainty
      </footer>
    </div>
  )
}
