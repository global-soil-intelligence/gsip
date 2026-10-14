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
import { LibrarySection } from './LibrarySection'
import {
  type LibraryDraft,
  isLibraryIntakeLive,
  queueLibraryDraft,
} from './library'
import { legalLinks } from './legal'
import { MySoil } from './MySoilPanel'
import { mySoil } from './mySoil'
import {
  type CapturedPhoto,
  isNativeApp,
  type LocationProblem,
  type Platform,
  type PhotoProblem,
  PhotoRefused,
  selectPlatform,
  webPlatform,
} from './platform'
import { photoFromFile, queuedPhoto } from './platform/camera'
import { siteLink } from './platform/links'
import {
  CLIENT_VERSION,
  type LocationSource,
  weakestMethod,
} from './provenance'
import {
  clearDraftPhotos,
  clearLibraryDraft,
  discardLibraryConflicts,
  savedLibraryDraft,
  saveLibraryDraft,
  queueRevision,
  putIfCurrent,
  discardHeld,
  draftPhotos,
  enqueue,
  indexedDbQueue,
  queued,
  reconfirmTerms,
  releaseHeld,
  retryDeadLettered,
  saveDraftPhoto,
  indexedDbReminderStore,
  queueReminderContext,
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
import { selectReminderNotifications } from './platform/notifications'
import { createSyncReminder, type ReminderView } from './syncReminder'

// Files created after this moment were taken with the camera during this visit (WP-6e claim).
const PAGE_LOADED_AT =
  typeof performance !== 'undefined' && performance.timeOrigin > 0
    ? performance.timeOrigin
    : Date.now()
const PAUSED_MESSAGE =
  'Capture is paused. Your observations stay safely on this device until it reopens.'
const LOCATION_PROBLEMS: Record<LocationProblem, string> = {
  denied:
    'Location was not shared. Allow it in your settings, or use the manual fallback below.',
  off: 'Location services are off on this device. Turn them on, or use the manual fallback below.',
  timeout:
    'Finding your location took too long. Try again in the open, or use the manual fallback below.',
  unavailable: 'Location is unavailable. Enter a latitude and longitude below.',
}
const PHOTO_PROBLEMS: Record<PhotoProblem, string> = {
  failed: 'The photo could not be taken. Try again.',
  no_camera: 'This device has no camera. Use a saved photo instead.',
  not_jpeg: 'Choose JPEG photos before continuing.',
  permission_denied:
    'Camera access is off for GSIP. Allow it in Settings, or use a saved photo.',
  too_large:
    'That photo is larger than 12 MB, so it could never upload. Take or choose a smaller one.',
}
const SHOTS: ShotType[] = ['A', 'B', 'C']
type ShotPhotos = Record<ShotType, CapturedPhoto | null>
const NO_PHOTOS: ShotPhotos = { A: null, B: null, C: null }
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
  onChooseFile,
  savedPhoto,
  shot,
}: {
  savedPhoto?: CapturedPhoto | null
  shot?: ShotType
  onChooseFile?: (file: File) => void
  label: string
  name: string
  optional?: boolean
}) {
  const preview = usePreview(savedPhoto ?? null)
  return (
    <label className="photo-field">
      <span>{label}</span>
      <small>{optional ? 'Optional confidence boost' : 'Required'}</small>
      {savedPhoto && <small>Photo {shot} ready on this device</small>}
      {preview && (
        <img
          className="photo-preview"
          src={preview}
          alt={`Saved draft photo ${shot}`}
        />
      )}
      <div className="camera-guide" aria-hidden="true">
        <span>Keep card + soil inside the guide</span>
      </div>
      <input
        name={name}
        type="file"
        accept="image/jpeg"
        capture="environment"
        required={!optional && !onChooseFile}
        onChange={(event) => {
          const file = event.currentTarget.files?.[0]
          if (file && onChooseFile) onChooseFile(file)
        }}
      />
    </label>
  )
}

/** The photo chosen for each shot, read once from the form's own file inputs. */
function selectedFiles(form: HTMLFormElement): Record<ShotType, File | null> {
  const fileFor = (shotType: ShotType): File | null => {
    const input = form.elements.namedItem(`shot-${shotType.toLowerCase()}`)
    const file =
      input instanceof HTMLInputElement ? input.files?.[0] : undefined
    return file && file.size ? file : null
  }
  return { A: fileFor('A'), B: fileFor('B'), C: fileFor('C') }
}

/** A browser's chosen files as captured photos, with their timestamps and claims. */
async function webPhotos(
  form: HTMLFormElement,
  now: number,
): Promise<ShotPhotos> {
  const files = selectedFiles(form)
  const entries = await Promise.all(
    SHOTS.map(async (shot) => {
      const file = files[shot]
      return [
        shot,
        file ? await photoFromFile(file, PAGE_LOADED_AT, now) : null,
      ] as const
    }),
  )
  return Object.fromEntries(entries) as ShotPhotos
}

/** A preview of a photo the app took, for the person to check the card is in frame. */
function usePreview(photo: CapturedPhoto | null): string | null {
  const [url, setUrl] = useState<string | null>(null)
  useEffect(() => {
    if (!photo || typeof URL.createObjectURL !== 'function') {
      setUrl(null)
      return
    }
    const next = URL.createObjectURL(
      new Blob([photo.bytes as Uint8Array<ArrayBuffer>], {
        type: photo.mimeType,
      }),
    )
    setUrl(next)
    return () => URL.revokeObjectURL(next)
  }, [photo])
  return url
}

/**
 * The phone app's shot: the native camera, or a saved photo through the web view's file input,
 * whose system picker needs no permission and converts iPhone HEIC photos to JPEG.
 */
function NativePhotoField({
  disabled,
  label,
  onChooseFile,
  onTake,
  optional = false,
  photo,
  shot,
}: {
  disabled: boolean
  label: string
  onChooseFile: (file: File) => void
  onTake: () => void
  optional?: boolean
  photo: CapturedPhoto | null
  shot: ShotType
}) {
  const preview = usePreview(photo)
  return (
    <div
      className="photo-field"
      role="group"
      aria-labelledby={`shot-${shot}-label`}
    >
      <span id={`shot-${shot}-label`}>{label}</span>
      <small>{optional ? 'Optional confidence boost' : 'Required'}</small>
      {preview ? (
        <img
          className="photo-preview"
          src={preview}
          alt={`Photo ${shot} as taken`}
        />
      ) : (
        <div className="camera-guide" aria-hidden="true">
          <span>Keep card + soil inside the guide</span>
        </div>
      )}
      <p className="photo-state" aria-live="polite">
        {photo ? `Photo ${shot} ready` : `No photo ${shot} yet`}
      </p>
      <div className="photo-actions">
        <button type="button" disabled={disabled} onClick={onTake}>
          {photo ? `Retake photo ${shot}` : `Take photo ${shot}`}
        </button>
        <label className="file-button">
          Use a saved photo for {shot}
          <input
            className="visually-hidden"
            name={`shot-${shot.toLowerCase()}`}
            type="file"
            accept="image/jpeg"
            disabled={disabled}
            onChange={(event) => {
              const file = event.currentTarget.files?.[0]
              event.currentTarget.value = ''
              if (file) onChooseFile(file)
            }}
          />
        </label>
      </div>
    </div>
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
      <a className="card-link" href={siteLink('../map/')}>
        Explore the map ↗
      </a>
    </section>
  )
}

export function App() {
  const formRef = useRef<HTMLFormElement>(null)
  const live = isCaptureLive()
  const libraryLive = isLibraryIntakeLive()
  const [libraryDraft, setLibraryDraft] = useState<LibraryDraft | null>(null)
  const [libraryConflictCount, setLibraryConflictCount] = useState(0)
  const [heldLibraryCount, setHeldLibraryCount] = useState(0)
  // WP-APP-1: the phone app uses the native camera and location; browsers use the web ones.
  const native = useMemo(() => isNativeApp(), [])
  const [platform, setPlatform] = useState<Platform | null>(() =>
    native ? null : webPlatform(),
  )
  const [nativePhotos, setNativePhotos] = useState<ShotPhotos>(NO_PHOTOS)
  // Camera and picker share one intent counter per shot: a later choice always wins.
  const photoRequests = useRef<Record<ShotType, number>>({ A: 0, B: 0, C: 0 })
  const [soilRefresh, setSoilRefresh] = useState(0)
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
  // True while this screen is open. A closed screen starts no drain and sends nothing more, so
  // it never races the next screen (or a reopened app) for the same queued record.
  const open = useRef(false)
  const queueSection = useRef<HTMLElement>(null)
  const reminderAccess = useRef<{ owner: string | null; gate: ServiceState }>({
    owner: null,
    gate: 'unknown',
  })
  const [reminderView, setReminderView] = useState<ReminderView>({
    enabled: false,
    outcome: native ? 'off' : 'unsupported',
  })
  const [reminderBusy, setReminderBusy] = useState(false)
  const reminder = useMemo(
    () =>
      createSyncReminder({
        notifications: selectReminderNotifications(native),
        store: indexedDbReminderStore,
        context: () =>
          queueReminderContext(
            reminderAccess.current.owner,
            live,
            reminderAccess.current.gate,
            libraryLive,
          ),
        focusQueue: () => queueSection.current?.focus(),
        changed: (view) => {
          if (open.current) setReminderView(view)
        },
      }),
    [native, live, libraryLive],
  )
  const observeServiceState = useCallback(
    (state: ServiceState) => {
      if (reminderAccess.current.gate !== state) {
        reminderAccess.current.gate = state
        if (native) void reminder.gatesChanged().then(() => reminder.refresh())
      }
      setServiceState(state)
    },
    [native, reminder],
  )
  const links = legalLinks()
  const loadMySoil = useCallback(
    () => (client ? mySoil(client) : Promise.resolve(null)),
    [client],
  )

  useEffect(() => {
    if (platform) return
    let cancelled = false
    selectPlatform().then(
      (loaded) => {
        if (!cancelled) setPlatform(loaded)
      },
      () => {
        if (!cancelled)
          setStatus(
            'The camera and location could not start. Close and reopen the app.',
          )
      },
    )
    return () => {
      cancelled = true
    }
  }, [platform])

  // Photos taken before Android ended the app (it may, while the camera is open) come back.
  useEffect(() => {
    if (!native && !libraryLive) return
    let cancelled = false
    draftPhotos().then(
      (saved) => {
        if (cancelled) return
        setNativePhotos((current) => ({
          A: current.A ?? saved.A ?? null,
          B: current.B ?? saved.B ?? null,
          C: current.C ?? saved.C ?? null,
        }))
      },
      () => undefined,
    )
    return () => {
      cancelled = true
    }
  }, [native, libraryLive])

  useEffect(() => {
    if (!libraryLive) return
    let cancelled = false
    void savedLibraryDraft().then((saved) => {
      if (!cancelled) setLibraryDraft(saved ?? null)
    })
    return () => {
      cancelled = true
    }
  }, [libraryLive])

  async function changeLibraryDraft(next: LibraryDraft | null) {
    const revision = next?.deviceRevision ?? (await queueRevision())
    setLibraryDraft(next)
    try {
      if (next) {
        if (!(await saveLibraryDraft(next, revision))) setLibraryDraft(null)
      } else await clearLibraryDraft()
    } catch {
      setStatus(
        'The private draft could not be saved. Try again before queueing.',
      )
    }
  }

  const refreshQueueState = useCallback(async () => {
    const records = await queued()
    if (!open.current) return records
    setQueueCount(records.length)
    setDeadLetterCount(
      records.filter((record) => Boolean(record.deadLetteredAt)).length,
    )
    setHeldCount(records.filter((record) => Boolean(record.heldAt)).length)
    setHeldLibraryCount(
      records.filter((record) => record.heldAt && record.library).length,
    )
    setLibraryConflictCount(
      records.filter((record) => Boolean(record.libraryConflictAt)).length,
    )
    setReconfirmCount(
      records.filter((record) => Boolean(record.termsExpiredAt)).length,
    )
    if (native) void reminder.refresh()
    return records
  }, [native, reminder])
  const drainOnce = useCallback(async () => {
    const closed = () => !open.current
    if (!client || !navigator.onLine || closed()) return
    const records = await indexedDbQueue.list()
    if (closed()) return
    if (!records.some((record) => isSyncEligible(record))) {
      await refreshQueueState()
      return
    }
    // Re-read the gate before every drain: capture can close or reopen while the app is
    // open, and a closed gate must not burn the queued records' retry budget.
    const state = await fetchServiceState(client)
    if (closed()) return
    observeServiceState(state)
    if (state === 'closed') {
      await refreshQueueState()
      setStatus(PAUSED_MESSAGE)
      return
    }
    setStatus('Securely syncing queued observations…')
    const result = await drainQueue(
      indexedDbQueue,
      (record, checkpoint) =>
        record.library
          ? submitQueued(client, record, checkpoint)
          : submitQueued(client, record),
      () => Date.now(),
      closed,
    )
    if (result.synced) {
      setSoilRefresh((count) => count + 1)
      if (native) void reminder.synced()
    }
    const remaining = await refreshQueueState()
    const deadLetters = remaining.filter((record) =>
      Boolean(record.deadLetteredAt),
    ).length
    const withdrawn = result.discarded
      ? ` ${result.discarded} observation${result.discarded > 1 ? 's' : ''} you had withdrawn ${result.discarded > 1 ? 'were' : 'was'} removed from this device.`
      : ''
    if (result.conflicts) {
      setStatus(
        'A private sample has an identity or context conflict. Keep it here or explicitly discard it; its identifiers cannot be replaced on retry.',
      )
    } else if (result.paused) {
      setStatus(
        'Private library intake is paused. Your sample and photos stay on this device, including any completed upload stage.',
      )
    } else if (result.reconfirm) {
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
  }, [client, native, observeServiceState, refreshQueueState, reminder])

  // One drain at a time. A trigger that arrives mid-drain (coming online, the gate reopening, the
  // retry timer) is never dropped: it schedules exactly one follow-up drain, however many arrive.
  const sync = useCallback(() => {
    const start = (): Promise<void> => {
      if (!open.current) return Promise.resolve()
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
    open.current = true
    return () => {
      open.current = false
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    void (async () => {
      if (client) {
        const state = await fetchServiceState(client)
        if (cancelled) return
        observeServiceState(state)
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
  }, [client, observeServiceState, refreshQueueState, sync])

  useEffect(() => {
    if (!native) return
    let observing = true
    void reminder.start()
    // Reuse the existing client. The callback is synchronous and keeps only the user ID,
    // never a session/token or a new client/auth/network path.
    let unsubscribe = () => undefined as void
    try {
      const subscription = client?.auth?.onAuthStateChange?.(
        (event, session) => {
          if (!observing) return
          try {
            const owner = session?.user.id ?? null
            const previous = reminderAccess.current.owner
            reminderAccess.current.owner = owner
            if (
              event === 'SIGNED_OUT' ||
              (event !== 'INITIAL_SESSION' && previous !== owner)
            )
              void reminder.hold().then(() => {
                if (observing) void reminder.refresh()
              })
            else void reminder.refresh()
          } catch {
            reminderAccess.current.owner = null
            void reminder.hold()
          }
        },
      ).data.subscription
      unsubscribe = () => {
        try {
          subscription?.unsubscribe()
        } catch {
          /* Auth callback errors stay private. */
        }
      }
    } catch {
      reminderAccess.current.owner = null
      void reminder.hold()
    }
    const refresh = () => {
      if (observing) void reminder.refresh()
    }
    const onVisible = () => {
      if (document.visibilityState === 'visible') refresh()
    }
    window.addEventListener('focus', refresh)
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      observing = false
      unsubscribe()
      window.removeEventListener('focus', refresh)
      document.removeEventListener('visibilitychange', onVisible)
      void reminder.stop()
    }
  }, [client, native, reminder])

  async function locate() {
    if (!platform) return
    setStatus('Requesting location permission…')
    const result = await platform.location.locate()
    if (!result.ok) {
      setStatus(LOCATION_PROBLEMS[result.problem])
      return
    }
    setLatitude(result.fix.latitude.toFixed(6))
    setLongitude(result.fix.longitude.toFixed(6))
    setAccuracy(result.fix.accuracyM)
    setLocationSource(result.fix.source)
    setStatus(
      'Location captured. It stays private; only a shared H3 cell can become public.',
    )
  }

  async function keepNativePhoto(
    shot: ShotType,
    photo: CapturedPhoto,
    revision: number,
  ) {
    if (revision !== (await queueRevision())) return
    setNativePhotos((current) => ({ ...current, [shot]: photo }))
    await saveDraftPhoto(shot, photo, revision)
    setStatus(`Photo ${shot} is ready.`)
  }

  async function takeNativePhoto(shot: ShotType) {
    if (platform?.camera.kind !== 'native') return
    const request = ++photoRequests.current[shot]
    const revision = await queueRevision()
    setStatus('Opening the camera… If it does not open, use a saved photo.')
    try {
      const photo = await platform.camera.takePhoto()
      if (request !== photoRequests.current[shot]) return
      if (photo) await keepNativePhoto(shot, photo, revision)
      else setStatus('No photo was taken.')
    } catch (error) {
      if (request !== photoRequests.current[shot]) return
      setStatus(
        PHOTO_PROBLEMS[
          error instanceof PhotoRefused ? error.problem : 'failed'
        ],
      )
    }
  }

  async function chooseNativePhoto(shot: ShotType, file: File) {
    const request = ++photoRequests.current[shot]
    const revision = await queueRevision()
    try {
      const photo = await photoFromFile(file, PAGE_LOADED_AT, Date.now())
      if (request !== photoRequests.current[shot]) return
      await keepNativePhoto(shot, photo, revision)
    } catch (error) {
      if (request !== photoRequests.current[shot]) return
      setStatus(
        PHOTO_PROBLEMS[
          error instanceof PhotoRefused ? error.problem : 'not_jpeg'
        ],
      )
    }
  }

  function discardNativePhotos() {
    for (const shot of SHOTS) photoRequests.current[shot] += 1
    setNativePhotos(NO_PHOTOS)
    setLibraryDraft(null)
    void clearDraftPhotos().catch(() => undefined)
    setStatus('Photos discarded.')
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
        'input[type="file"][name^="shot-"]',
      ),
    ).some((input) =>
      Array.from(input.files ?? []).some((file) => file.type !== 'image/jpeg'),
    )
    if (unsupportedPhoto) {
      setStatus('Choose JPEG photos before continuing.')
      return
    }
    const formElement = event.currentTarget
    const form = new FormData(formElement)
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
    const submitRevision = await queueRevision()
    const now = Date.now()
    let shots: ShotPhotos
    try {
      shots =
        native || libraryLive ? nativePhotos : await webPhotos(formElement, now)
    } catch (error) {
      setStatus(
        PHOTO_PROBLEMS[
          error instanceof PhotoRefused ? error.problem : 'not_jpeg'
        ],
      )
      return
    }
    // SPEC I2: shots A and B are required; the browser's `required` covers only its own form.
    if (!shots.A || !shots.B) {
      setStatus('Add photos A and B before continuing.')
      return
    }
    const capturedPhotos = SHOTS.flatMap((shot) => {
      const photo = shots[shot]
      return photo ? [queuedPhoto(photo, shot)] : []
    })
    // WP-6d: an observation is only ever sent as the account it was made under.
    const ownerUid = await recordOwner(client)
    let library: QueueRecord['library']
    if (libraryDraft) {
      if (libraryDraft.ownerUid && libraryDraft.ownerUid !== ownerUid) {
        setStatus(
          'This private draft belongs to its original account. Return to that account or discard the draft before creating a new sample.',
        )
        return
      }
      try {
        library = queueLibraryDraft(libraryDraft)
      } catch {
        setStatus(
          'Enter valid sample depth bounds and a supported declaration before queueing.',
        )
        return
      }
      // Persist private context and photo bytes before the durable queue write.
      if (
        libraryDraft.deviceRevision !== undefined &&
        libraryDraft.deviceRevision !== submitRevision
      )
        return
      if (!(await saveLibraryDraft(libraryDraft, submitRevision))) return
      await Promise.all(
        SHOTS.flatMap((shot) =>
          shots[shot]
            ? [saveDraftPhoto(shot, shots[shot]!, submitRevision)]
            : [],
        ),
      )
    }
    const record: QueueRecord = {
      accuracyM: accuracy,
      acceptedAt: new Date(now).toISOString(),
      attributionName,
      capturedAt: captureTime({ lastModified: shots.B.takenAt }, now),
      // WP-6e: claims only. The server never lets them raise a provenance tier.
      claims: {
        captureMethod: weakestMethod([shots.A.method, shots.B.method]),
        clientVersion: CLIENT_VERSION,
        ingestPath: platform?.ingestPath ?? (native ? 'app' : 'web'),
        locationSource,
      },
      deviceModel: coarseDeviceModel(),
      disturbed: form.get('disturbed') === 'yes',
      grantId: crypto.randomUUID(),
      library,
      landCover: String(form.get('land-cover')),
      latitude: numericLatitude,
      longitude: numericLongitude,
      ownerUid,
      photos: capturedPhotos,
      queuedAt: new Date().toISOString(),
      submissionId: library?.request.submission_id ?? crypto.randomUUID(),
      surfaceCondition: String(form.get('surface-condition')),
      termsVersion: TERMS_VERSION,
    }
    if (library) {
      if (!(await putIfCurrent(record, submitRevision, false))) return
    } else await enqueue(record)
    setLibraryDraft(null)
    setPublicCell(fuzzLocation(numericLatitude, numericLongitude).h3R8)
    formRef.current?.reset()
    setNativePhotos(NO_PHOTOS)
    await clearDraftPhotos().catch(() => undefined)
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
        <a
          className="brand"
          href={siteLink('../map/')}
          aria-label="GSIP public map"
        >
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
            href={siteLink(
              '../reference-card/gsip-reference-card-v1-color.pdf',
            )}
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
                {native
                  ? 'Submit anonymously: no sign-up is needed.'
                  : 'Submit anonymously now, or use a magic link to keep contributing from more than one device.'}
              </p>
            </div>
            {native ? (
              <p className="field-hint">
                Your contributions belong to this phone’s private account.
                E-mail sign-in, to use the same account on other devices, comes
                in a later version of the app.
              </p>
            ) : (
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
            )}
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
                {native ? (
                  (
                    [
                      ['A', 'A · Context / 30 cm', false],
                      ['B', 'B · Fresh face / 15 cm', false],
                      ['C', 'C · Moist texture', true],
                    ] as const
                  ).map(([shot, label, optional]) => (
                    <NativePhotoField
                      key={shot}
                      disabled={platform === null}
                      label={label}
                      optional={optional}
                      photo={nativePhotos[shot]}
                      shot={shot}
                      onChooseFile={(file) =>
                        void chooseNativePhoto(shot, file)
                      }
                      onTake={() => void takeNativePhoto(shot)}
                    />
                  ))
                ) : (
                  <>
                    <PhotoField
                      savedPhoto={libraryLive ? nativePhotos.A : undefined}
                      shot="A"
                      name="shot-a"
                      label="A · Context / 30 cm"
                      onChooseFile={
                        libraryLive
                          ? (file) => void chooseNativePhoto('A', file)
                          : undefined
                      }
                    />
                    <PhotoField
                      savedPhoto={libraryLive ? nativePhotos.B : undefined}
                      shot="B"
                      name="shot-b"
                      label="B · Fresh face / 15 cm"
                      onChooseFile={
                        libraryLive
                          ? (file) => void chooseNativePhoto('B', file)
                          : undefined
                      }
                    />
                    <PhotoField
                      savedPhoto={libraryLive ? nativePhotos.C : undefined}
                      shot="C"
                      onChooseFile={
                        libraryLive
                          ? (file) => void chooseNativePhoto('C', file)
                          : undefined
                      }
                      name="shot-c"
                      label="C · Moist texture"
                      optional
                    />
                  </>
                )}
              </div>
              {native &&
                (nativePhotos.A || nativePhotos.B || nativePhotos.C) && (
                  <button
                    type="button"
                    className="secondary discard-photos"
                    onClick={discardNativePhotos}
                  >
                    Discard these photos
                  </button>
                )}
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
                disabled={platform === null}
                onClick={() => void locate()}
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

            {libraryLive && (
              <LibrarySection
                client={client}
                value={libraryDraft}
                onChange={changeLibraryDraft}
              />
            )}
            {libraryLive && !native && (
              <button
                type="button"
                className="secondary"
                onClick={discardNativePhotos}
              >
                Discard draft photos and private sample
              </button>
            )}
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

        <section
          ref={queueSection}
          tabIndex={-1}
          className="status-card"
          aria-live="polite"
        >
          <div>
            <p className="step-number">Status</p>
            <h2>{status}</h2>
            {native && (
              <div role="group" aria-label="Device sync reminders">
                <h3>Sync reminders</h3>
                <p>
                  One optional reminder to review unsynced work after about a
                  day. Delivery can be delayed by your phone.
                </p>
                <button
                  type="button"
                  disabled={
                    reminderBusy ||
                    reminderView.enabled ||
                    reminderView.outcome === 'unsupported' ||
                    !live ||
                    serviceState !== 'open' ||
                    !client
                  }
                  onClick={() => {
                    setReminderBusy(true)
                    void reminder.enable().finally(() => setReminderBusy(false))
                  }}
                >
                  Enable sync reminders
                </button>
                <button
                  type="button"
                  className="secondary"
                  disabled={!reminderView.enabled && !reminderBusy}
                  onClick={() => {
                    void reminder.disable()
                  }}
                >
                  Turn off sync reminders
                </button>
                <p role="status">
                  {reminderView.outcome === 'cleanup_pending'
                    ? 'Device reminder cleanup is pending. Open GSIP again to retry.'
                    : reminderView.outcome === 'unsupported'
                      ? 'Reminders are unavailable on this device. Capture still works.'
                      : reminderView.outcome === 'permission_denied'
                        ? 'Reminders are off. You can keep using GSIP.'
                        : reminderView.outcome === 'held'
                          ? 'Reminders are paused until this device and queued work are ready.'
                          : reminderView.enabled
                            ? 'Sync reminders are on.'
                            : 'Sync reminders are off.'}
                </p>
              </div>
            )}
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
                {heldLibraryCount > 0 && (
                  <p>
                    Private library samples stay bound to their original
                    account. Return to that account to retry; this button cannot
                    transfer them.
                  </p>
                )}
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
                    void recordOwner(client)
                      .then((uid) => releaseHeld(uid))
                      .then(refreshQueueState)
                      .then(() => sync())
                  }}
                >
                  {heldLibraryCount === heldCount
                    ? 'Retry from the original account'
                    : 'Send'}{' '}
                  {heldCount > 1 ? 'them' : 'it'} from this device’s account
                </button>
              </div>
            )}
            {libraryConflictCount > 0 && (
              <div role="group" aria-label="Private samples needing attention">
                <p>
                  {libraryConflictCount} private sample(s) have an immutable
                  identity or context conflict. They remain on this device until
                  you discard them.
                </p>
                <button
                  type="button"
                  className="secondary"
                  onClick={() =>
                    void discardLibraryConflicts().then(refreshQueueState)
                  }
                >
                  Discard conflicted private samples
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
          <MySoil load={loadMySoil} refreshKey={soilRefresh} />
        )}

        {live && client && (
          <YourData
            client={client}
            onBeforeRightsRequest={() =>
              native ? reminder.hold() : Promise.resolve()
            }
            onQueueCleared={async () => {
              // The queue and any photos taken here are gone; My Soil changes too.
              for (const shot of SHOTS) photoRequests.current[shot] += 1
              setNativePhotos(NO_PHOTOS)
              setLibraryDraft(null)
              setSoilRefresh((count) => count + 1)
              await refreshQueueState()
            }}
          />
        )}
      </main>
      <footer>
        Open science · Privacy-safe by default · Estimates include uncertainty
      </footer>
    </div>
  )
}
