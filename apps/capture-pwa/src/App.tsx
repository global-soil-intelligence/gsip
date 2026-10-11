import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ATTRIBUTION_MAX_LENGTH,
  DEFAULT_ATTRIBUTION,
  attributionProblem,
  normalizeAttribution,
} from '@gsip/schema'
import { captureTime, isCaptureLive } from './capture'
import { fuzzLocation } from './geo'
import { HexPreview } from './HexPreview'
import { legalLinks } from './legal'
import { captureMethod, ingestPath, type LocationSource } from './provenance'
import {
  discardHeld,
  enqueue,
  indexedDbQueue,
  queued,
  reconfirmTerms,
  releaseHeld,
  retryDeadLettered,
} from './queue'
import { drainQueue, isSyncEligible } from './sync'
import {
  createGsipClient,
  fetchServiceState,
  isServiceConfigured,
  recordOwner,
  sendSignInLink,
  type ServiceState,
  submitQueued,
} from './supabase'
import { TERMS_VERSION } from './terms'
import type { QueueRecord, ShotType } from './types'
import { YourData } from './YourData'

// Files created after this moment were taken with the camera during this visit (WP-6e claim).
const PAGE_LOADED_AT =
  typeof performance !== 'undefined' && performance.timeOrigin > 0
    ? performance.timeOrigin
    : Date.now()
const PAUSED_MESSAGE =
  'Capture is paused. Your observations stay safely on this device until it reopens.'
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
        accept="image/jpeg"
        capture="environment"
        required={!optional}
      />
    </label>
  )
}

type SelectedPhotos = Record<ShotType, File | null>

/** The photo chosen for each shot, read once from the form's own file inputs. */
function selectedPhotos(form: HTMLFormElement): SelectedPhotos {
  const fileFor = (shotType: ShotType): File | null => {
    const input = form.elements.namedItem(`shot-${shotType.toLowerCase()}`)
    const file =
      input instanceof HTMLInputElement ? input.files?.[0] : undefined
    return file && file.size ? file : null
  }
  return { A: fileFor('A'), B: fileFor('B'), C: fileFor('C') }
}

async function photos(
  selected: SelectedPhotos,
): Promise<QueueRecord['photos']> {
  const readBytes = async (file: File) =>
    new Uint8Array(await file.arrayBuffer())
  const captured = await Promise.all(
    (['A', 'B', 'C'] as ShotType[]).map(async (shotType) => {
      const file = selected[shotType]
      if (file && file.type !== 'image/jpeg') {
        throw new Error('Only JPEG photos can be queued.')
      }
      return file
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

export function coarseDeviceModel(): string {
  const navigatorWithHints = navigator as Navigator & {
    userAgentData?: { brands?: Array<{ brand: string }>; platform?: string }
  }
  const hints = navigatorWithHints.userAgentData
  if (hints?.platform) {
    const brands = hints.brands?.map(({ brand }) => brand).join(', ')
    return [hints.platform, brands].filter(Boolean).join('; ').slice(0, 160)
  }
  const family = navigator.userAgent.match(
    /Android|iPhone|iPad|Macintosh|Windows|Linux/i,
  )?.[0]
  return family ?? 'unknown device'
}

function CaptureClosed() {
  return (
    <section className="closed-card" aria-labelledby="closed-heading">
      <p className="step-number">Opening soon</p>
      <h2 id="closed-heading">Contributions open after our launch review.</h2>
      <p>
        GSIP is completing its privacy and legal review before accepting
        observations. You can print the reference card and explore the public
        map now.
      </p>
      <a className="card-link" href="../map/">
        Explore the map ↗
      </a>
    </section>
  )
}

export function App() {
  const formRef = useRef<HTMLFormElement>(null)
  const live = isCaptureLive()
  const client = useMemo(
    () =>
      isCaptureLive() && isServiceConfigured() ? createGsipClient() : null,
    [],
  )
  const [serviceState, setServiceState] = useState<ServiceState>('unknown')
  const [attributionError, setAttributionError] = useState<string | null>(null)
  const [accuracy, setAccuracy] = useState<number | null>(null)
  const [latitude, setLatitude] = useState('')
  const [longitude, setLongitude] = useState('')
  const [locationSource, setLocationSource] =
    useState<LocationSource>('unknown')
  const [queueCount, setQueueCount] = useState(0)
  const [deadLetterCount, setDeadLetterCount] = useState(0)
  const [heldCount, setHeldCount] = useState(0)
  const [reconfirmCount, setReconfirmCount] = useState(0)
  const [emailInUse, setEmailInUse] = useState(false)
  const [status, setStatus] = useState('Ready for your first observation.')
  const [publicCell, setPublicCell] = useState<string | null>(null)
  const [email, setEmail] = useState('')
  const syncPromise = useRef<Promise<void> | null>(null)
  const syncAgain = useRef(false)
  const links = legalLinks()

  const refreshQueueState = useCallback(async () => {
    const records = await queued()
    setQueueCount(records.length)
    setDeadLetterCount(
      records.filter((record) => Boolean(record.deadLetteredAt)).length,
    )
    setHeldCount(records.filter((record) => Boolean(record.heldAt)).length)
    setReconfirmCount(
      records.filter((record) => Boolean(record.termsExpiredAt)).length,
    )
    return records
  }, [])
  const drainOnce = useCallback(async () => {
    if (!client || !navigator.onLine) return
    const records = await indexedDbQueue.list()
    if (!records.some((record) => isSyncEligible(record))) {
      await refreshQueueState()
      return
    }
    // Re-read the gate before every drain: capture can close or reopen while the app is
    // open, and a closed gate must not burn the queued records' retry budget.
    const state = await fetchServiceState(client)
    setServiceState(state)
    if (state === 'closed') {
      await refreshQueueState()
      setStatus(PAUSED_MESSAGE)
      return
    }
    setStatus('Securely syncing queued observations…')
    const result = await drainQueue(indexedDbQueue, (record) =>
      submitQueued(client, record),
    )
    const remaining = await refreshQueueState()
    const deadLetters = remaining.filter((record) =>
      Boolean(record.deadLetteredAt),
    ).length
    const withdrawn = result.discarded
      ? ` ${result.discarded} observation${result.discarded > 1 ? 's' : ''} you had withdrawn ${result.discarded > 1 ? 'were' : 'was'} removed from this device.`
      : ''
    if (result.reconfirm) {
      setStatus(
        `${result.reconfirm} observation${result.reconfirm > 1 ? 's' : ''} waited more than 30 days to sync. Accept the contribution terms again to send ${result.reconfirm > 1 ? 'them' : 'it'}.${withdrawn}`,
      )
    } else if (result.held) {
      setStatus(
        `${result.held} observation${result.held > 1 ? 's belong' : ' belongs'} to an account that is no longer signed in here, so ${result.held > 1 ? 'they were' : 'it was'} not sent.${withdrawn}`,
      )
    } else if (deadLetters) {
      setStatus(
        `${deadLetters} observation${deadLetters > 1 ? 's need' : ' needs'} attention before retrying.`,
      )
    } else if (result.failed) {
      setStatus(
        'Sync paused. Your observation remains safely queued on this device.',
      )
    } else if (result.synced) {
      setStatus(
        `${result.synced} observation${result.synced > 1 ? 's' : ''} synced.${withdrawn}`,
      )
    } else if (withdrawn) {
      setStatus(withdrawn.trim())
    } else {
      setStatus('Ready for your next observation.')
    }
  }, [client, refreshQueueState])

  // One drain at a time. A trigger that arrives mid-drain (coming online, the gate reopening, the
  // retry timer) is never dropped: it schedules exactly one follow-up drain, however many arrive.
  const sync = useCallback(() => {
    const start = (): Promise<void> => {
      if (syncPromise.current) {
        syncAgain.current = true
        return syncPromise.current
      }
      const run = drainOnce()
      syncPromise.current = run
      const settle = () => {
        if (syncPromise.current !== run) return
        syncPromise.current = null
        if (syncAgain.current) {
          syncAgain.current = false
          void start()
        }
      }
      void run.then(settle, settle)
      return run
    }
    return start()
  }, [drainOnce])

  useEffect(() => {
    let cancelled = false
    void (async () => {
      if (client) {
        const state = await fetchServiceState(client)
        if (cancelled) return
        setServiceState(state)
      }
      await refreshQueueState()
      if (!cancelled) await sync()
    })()
    const onOnline = () => void sync()
    const retry = window.setInterval(() => void sync(), 30_000)
    window.addEventListener('online', onOnline)
    return () => {
      cancelled = true
      window.clearInterval(retry)
      window.removeEventListener('online', onOnline)
    }
  }, [client, refreshQueueState, sync])

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
        setLocationSource('device_gps')
        setStatus(
          'Location captured. It stays private; only a shared H3 cell can become public.',
        )
      },
      () =>
        setStatus('Location was not shared. Use the manual fallback below.'),
      { enableHighAccuracy: true, maximumAge: 30_000, timeout: 15_000 },
    )
  }

  async function sendMagicLink(switchAccount = false) {
    if (!client || !email) return
    let outcome: Awaited<ReturnType<typeof sendSignInLink>>
    try {
      outcome = await sendSignInLink(
        client,
        email,
        window.location.href.split('#')[0],
        switchAccount,
      )
    } catch {
      outcome = 'failed'
    }
    setEmailInUse(outcome === 'email_in_use')
    setStatus(
      {
        confirm_sent:
          'Check your email to confirm it. Your contributions from this device stay with your account.',
        email_in_use:
          'That email already has an account. Signing in to it here leaves this device’s anonymous contributions with the anonymous account: withdraw them first under Your data if you want them removed.',
        failed: 'The sign-in link could not be sent. Try again.',
        sent: 'Check your email for the secure sign-in link.',
      }[outcome],
    )
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const unsupportedPhoto = Array.from(
      event.currentTarget.querySelectorAll<HTMLInputElement>(
        'input[type="file"]',
      ),
    ).some((input) =>
      Array.from(input.files ?? []).some((file) => file.type !== 'image/jpeg'),
    )
    if (unsupportedPhoto) {
      setStatus('Choose JPEG photos before continuing.')
      return
    }
    const selected = selectedPhotos(event.currentTarget)
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
    const attributionName = normalizeAttribution(
      String(form.get('attribution') ?? ''),
    )
    if (attributionProblem(attributionName)) {
      setAttributionError(
        'Use letters, numbers, spaces and simple punctuation, with no links or e-mail addresses.',
      )
      setStatus('Check the public attribution name before continuing.')
      return
    }
    setAttributionError(null)
    // WP-6d: the sampling and land-access rules are confirmed for every observation. The browser
    // enforces the required checkbox; this check also covers scripted submits.
    if (form.get('sampling-rules') !== 'on') {
      setStatus('Confirm the sampling rules before queueing this observation.')
      return
    }
    let capturedPhotos: QueueRecord['photos']
    try {
      capturedPhotos = await photos(selected)
    } catch {
      setStatus('Choose JPEG photos before continuing.')
      return
    }
    // WP-6d: an observation is only ever sent as the account it was made under.
    const ownerUid = await recordOwner(client)
    const now = Date.now()
    const record: QueueRecord = {
      accuracyM: accuracy,
      acceptedAt: new Date(now).toISOString(),
      attributionName,
      capturedAt: captureTime(selected.B, now),
      // WP-6e: claims only. The server never lets them raise a provenance tier.
      claims: {
        captureMethod: captureMethod(
          [selected.A, selected.B],
          PAGE_LOADED_AT,
          now,
        ),
        ingestPath: ingestPath(),
        locationSource,
      },
      deviceModel: coarseDeviceModel(),
      disturbed: form.get('disturbed') === 'yes',
      grantId: crypto.randomUUID(),
      landCover: String(form.get('land-cover')),
      latitude: numericLatitude,
      longitude: numericLongitude,
      ownerUid,
      photos: capturedPhotos,
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
    setLocationSource('unknown')
    await refreshQueueState()
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
          {deadLetterCount
            ? `${deadLetterCount} need${deadLetterCount > 1 ? '' : 's'} attention`
            : queueCount
              ? `${queueCount} queued`
              : navigator.onLine
                ? 'Online'
                : 'Offline ready'}
        </div>
      </header>

      <main>
        <section className="hero">
          <p className="eyebrow">Two photos. One card. One living planet.</p>
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

        {!live && <CaptureClosed />}

        {live && serviceState === 'closed' && (
          <p className="config-warning" role="status">
            {PAUSED_MESSAGE}
          </p>
        )}

        {live && (
          <section className="signin-card" aria-labelledby="signin-heading">
            <div>
              <p className="step-number">Optional account</p>
              <h2 id="signin-heading">Keep contributing privately</h2>
              <p>
                Submit anonymously now, or use a magic link to keep contributing
                from more than one device.
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
              {emailInUse && (
                <button
                  type="button"
                  className="secondary"
                  onClick={() => void sendMagicLink(true)}
                >
                  Sign in to that account instead
                </button>
              )}
            </div>
          </section>
        )}

        {live && (
          <form ref={formRef} onSubmit={(event) => void submit(event)}>
            <fieldset>
              <legend>
                <span>01</span> Capture the soil
              </legend>
              <p>
                Use even daylight. Keep the whole reference card visible and
                avoid glare.
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
                We store the exact point privately for scientific processing.
                Public maps and data show only a broad H3 cell shared with at
                least two other contributors.
              </p>
              <button
                type="button"
                className="location-button"
                onClick={locate}
              >
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
                    onChange={(event) => {
                      // A typed coordinate is a manual location; a GPS accuracy no longer applies.
                      setLatitude(event.target.value)
                      setLocationSource('manual_pin')
                      setAccuracy(null)
                    }}
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
                    onChange={(event) => {
                      setLongitude(event.target.value)
                      setLocationSource('manual_pin')
                      setAccuracy(null)
                    }}
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
                  maxLength={ATTRIBUTION_MAX_LENGTH}
                  required
                  defaultValue={DEFAULT_ATTRIBUTION}
                  aria-describedby="attribution-hint"
                  aria-invalid={attributionError ? true : undefined}
                />
              </label>
              <p className="field-hint" id="attribution-hint">
                {attributionError ??
                  'This name is published with your photo’s area and date. Keep the default to stay anonymous, or use a pseudonym rather than your real name.'}
              </p>
              <label className="terms">
                <input type="checkbox" name="sampling-rules" required />{' '}
                <span>
                  I had permission to dig here and followed the{' '}
                  <a
                    href={links.samplingRules}
                    target="_blank"
                    rel="noreferrer"
                  >
                    sampling rules
                  </a>
                  : not in a protected area, on a grave or heritage site, or
                  near buried utilities; soil replaced; no people in the photos.
                </span>
              </label>
              <label className="terms">
                <input type="checkbox" name="terms" required />{' '}
                <span>
                  I am at least 16, or a teacher contributing for my class. I
                  own these photos and grant GSIP permission to include
                  structured contribution data in the ODbL 1.0 database and
                  publish sanitized photos under CC BY-SA 4.0, under the{' '}
                  <a href={links.terms} target="_blank" rel="noreferrer">
                    contribution terms
                  </a>{' '}
                  and{' '}
                  <a href={links.privacy} target="_blank" rel="noreferrer">
                    privacy notice
                  </a>
                  . I understand this is an immutable acceptance snapshot for
                  this submission, and that I can withdraw it later.
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
        )}

        <section className="status-card" aria-live="polite">
          <div>
            <p className="step-number">Status</p>
            <h2>{status}</h2>
            {heldCount > 0 && (
              <div
                className="held-actions"
                role="group"
                aria-label="Observations from another account"
              >
                <p>
                  {heldCount} observation{heldCount > 1 ? 's were' : ' was'}{' '}
                  made under an account that is no longer signed in on this
                  device. {heldCount > 1 ? 'They stay' : 'It stays'} here and{' '}
                  {heldCount > 1 ? 'are' : 'is'} not sent unless you choose.
                </p>
                <button
                  type="button"
                  className="secondary"
                  onClick={() => {
                    void discardHeld().then(refreshQueueState)
                  }}
                >
                  Discard {heldCount > 1 ? 'them' : 'it'}
                </button>
                <button
                  type="button"
                  className="secondary"
                  onClick={() => {
                    void releaseHeld()
                      .then(refreshQueueState)
                      .then(() => sync())
                  }}
                >
                  Send {heldCount > 1 ? 'them' : 'it'} from this device’s
                  account
                </button>
              </div>
            )}
            {reconfirmCount > 0 && (
              <div
                className="held-actions"
                role="group"
                aria-label="Observations waiting for the contribution terms"
              >
                <p>
                  {reconfirmCount} observation
                  {reconfirmCount > 1 ? 's' : ''} waited more than 30 days to
                  sync, so the{' '}
                  <a href={links.terms} target="_blank" rel="noreferrer">
                    contribution terms
                  </a>{' '}
                  must be accepted again before{' '}
                  {reconfirmCount > 1 ? 'they are' : 'it is'} sent. Nothing else
                  about {reconfirmCount > 1 ? 'them' : 'it'} changes.
                </p>
                <button
                  type="button"
                  className="secondary"
                  onClick={() => {
                    void reconfirmTerms(new Date().toISOString(), TERMS_VERSION)
                      .then(refreshQueueState)
                      .then(() => sync())
                  }}
                >
                  Accept the terms again and send
                </button>
              </div>
            )}
            {deadLetterCount > 0 && (
              <button
                type="button"
                className="secondary"
                onClick={() => {
                  void retryDeadLettered()
                    .then(refreshQueueState)
                    .then(() => sync())
                }}
              >
                Retry failed observations
              </button>
            )}
          </div>
          {publicCell && <HexPreview cell={publicCell} />}
        </section>

        {live && client && (
          <YourData client={client} onQueueCleared={refreshQueueState} />
        )}
      </main>
      <footer>
        Open science · Privacy-safe by default · Estimates include uncertainty
      </footer>
    </div>
  )
}
