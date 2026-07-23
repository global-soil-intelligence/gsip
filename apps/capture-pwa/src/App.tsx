import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import { CaptureForm } from './CaptureForm'
import { captureEnabled } from './config'
import {
  enqueue,
  indexedDbQueue,
  queued,
  removeQueued,
  retryDeadLettered,
} from './queue'
import { drainQueue } from './sync'
import {
  connectEmail,
  createGsipClient,
  isServiceConfigured,
  observationHistory,
  submitQueued,
  type RemoteObservation,
} from './supabase'
import { listenNative, openResource } from './platform'
import type { QueueRecord } from './types'
export { coarseDeviceModel } from './CaptureForm'
const SoilMap = lazy(() =>
  import('../../map-web/src/App').then((m) => ({ default: m.App })),
)
type Tab = 'Explore' | 'Capture' | 'Observations' | 'Learn' | 'Account'
const tabs: Tab[] = ['Explore', 'Capture', 'Observations', 'Learn', 'Account']
const icons = [
  'M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3zM9 3v15M15 6v15',
  'M3 7h5l2-3h4l2 3h5v13H3zM16 13a4 4 0 1 1-8 0 4 4 0 0 1 8 0',
  'M7 3h14v18H7zM3 7h4M3 12h4M3 17h4M10 8h7M10 12h7M10 16h5',
  'M3 4h7l2 2 2-2h7v16h-7l-2 1-2-1H3zM12 6v15',
  'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0M4 21v-3a8 8 0 0 1 16 0v3',
]
function Icon({ index }: { index: number }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d={icons[index]} />
    </svg>
  )
}
const labelStatus = (row: RemoteObservation) =>
  !row.upload_completed_at
    ? 'Upload incomplete'
    : row.status === 'qa_pass'
      ? 'Accepted · awaiting release confirmation'
      : row.status === 'qa_fail'
        ? 'Needs a new observation'
        : row.status === 'flagged'
          ? 'Needs review'
          : 'Checking quality'

export function App() {
  const [tab, setTab] = useState<Tab>('Explore')
  const [records, setRecords] = useState<QueueRecord[]>([])
  const [remote, setRemote] = useState<RemoteObservation[]>([])
  const [detail, setDetail] = useState<RemoteObservation | null>(null)
  const [draft, setDraft] = useState<QueueRecord>()
  const [formKey, setFormKey] = useState('new')
  const [status, setStatus] = useState('Ready for your first observation.')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [online, setOnline] = useState(navigator.onLine)
  const [email, setEmail] = useState('')
  const [token, setToken] = useState('')
  const [otpType, setOtpType] = useState<'email' | 'email_change'>('email')
  const [sent, setSent] = useState(false)
  const [account, setAccount] = useState('No account connected')
  const client = useMemo(
    () => (isServiceConfigured() ? createGsipClient() : null),
    [],
  )
  const flight = useRef<Promise<void> | null>(null)
  const enabled = captureEnabled()
  const refresh = useCallback(async () => {
    const items = await queued()
    setRecords(items)
    return items
  }, [])
  const refreshRemote = useCallback(async () => {
    if (!client) return
    try {
      setRemote(await observationHistory(client))
      const { data } = await client.auth.getSession()
      setAccount(
        data.session?.user.email ??
          (data.session
            ? 'Anonymous contributor on this device'
            : 'No account connected'),
      )
    } catch (e) {
      setError(
        e instanceof Error ? e.message : 'Could not refresh your account.',
      )
    }
  }, [client])
  const sync = useCallback(() => {
    if (flight.current) return flight.current
    const run = (async () => {
      if (!client || !enabled || !navigator.onLine) return
      setSyncing(true)
      try {
        const result = await drainQueue(indexedDbQueue, (record) =>
          submitQueued(client, record),
        )
        if (result.synced)
          setStatus(
            `${result.synced} observation${result.synced > 1 ? 's' : ''} synced. Quality checks come next.`,
          )
        if (result.failed)
          setStatus(
            'Upload paused. Your observations remain on this device. Check your connection and account, then retry.',
          )
        await refresh()
        await refreshRemote()
      } catch {
        setError(
          'Could not access local observations. Please retry before closing the app.',
        )
      } finally {
        setSyncing(false)
      }
    })()
    flight.current = run
    void run.finally(() => {
      if (flight.current === run) flight.current = null
    })
    return run
  }, [client, enabled, refresh, refreshRemote])
  useEffect(() => {
    void refresh()
      .then(() => sync())
      .catch(() => setError('Local observation storage is unavailable.'))
    const network = () => {
      setOnline(navigator.onLine)
      void sync()
    }
    window.addEventListener('online', network)
    window.addEventListener('offline', network)
    const interval = window.setInterval(() => void sync(), 30000)
    let disposed = false
    let stop: (() => void) | undefined
    void listenNative(client, network, () =>
      setError('Sign-in link could not be completed. Request a new link.'),
    ).then((cleanup) => {
      if (disposed) cleanup()
      else stop = cleanup
    })
    return () => {
      disposed = true
      stop?.()
      window.clearInterval(interval)
      window.removeEventListener('online', network)
      window.removeEventListener('offline', network)
    }
  }, [client, refresh, sync])
  const go = (next: Tab) => {
    setTab(next)
    setDetail(null)
    if (next === 'Account' || next === 'Observations') void refreshRemote()
  }
  async function save(record: QueueRecord) {
    setBusy(true)
    try {
      await enqueue(record)
      await refresh()
      setStatus(
        record.draft
          ? 'Draft saved on this device. You can finish it in My observations.'
          : 'Saved offline. It will sync when GSIP is open and connected.',
      )
      if (!record.draft) {
        setDraft(undefined)
        setFormKey(crypto.randomUUID())
        go('Observations')
        await sync()
      }
    } finally {
      setBusy(false)
    }
  }
  const pending = records.filter((r) => !r.draft)
  const dead = pending.filter((r) => r.deadLetteredAt)
  const resource = (path: string) =>
    void openResource(path).catch(() =>
      setError('Could not open that resource. Please try again.'),
    )
  return (
    <div className="mobile-app">
      <header className="app-header">
        <button
          className="wordmark"
          onClick={() => go('Explore')}
          aria-label="GSIP home"
        >
          <span className="logo-mark">G</span>
          <span>
            GSIP<small>GLOBAL SOIL INTELLIGENCE</small>
          </span>
        </button>
        <span className="connection">
          <i className={online ? 'connected' : ''} />
          {online ? 'Online' : 'Offline'}
        </span>
      </header>
      <div className="app-content">
        {tab === 'Explore' && (
          <>
            <section className="welcome">
              <div>
                <p className="eyebrow">THE GROUND WE SHARE</p>
                <h1>
                  A living atlas.
                  <br />
                  <em>Built from the ground up.</em>
                </h1>
                <p>
                  Explore our soils. Add your perspective. Help build an open
                  record of the earth beneath us.
                </p>
                <button onClick={() => go('Capture')}>
                  {enabled ? 'Make an observation' : 'Capture opening soon'}{' '}
                  <span aria-hidden="true">↗</span>
                </button>
              </div>
              <div className="soil-art" aria-hidden="true">
                <div className="sprout" />
                <div className="soil-layer topsoil">SURFACE</div>
                <div className="soil-layer subsoil">A CLOSER LOOK</div>
                <div className="soil-layer bedrock">SHARED KNOWLEDGE</div>
              </div>
            </section>
            <section className="map-section">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">EXPLORE THE MAP</p>
                  <h2>Every place has a soil story.</h2>
                </div>
                <span className="tag">SoilGrids context</span>
              </div>
              <Suspense fallback={<p className="notice">Loading the map…</p>}>
                <SoilMap embedded onCapture={() => go('Capture')} />
              </Suspense>
              <p className="hint">
                These layers are existing map estimates. They are not
                measurements from a photograph. Community contributions appear
                as approximate cells.
              </p>
            </section>
            <div className="intro-grid">
              <section className="field-card">
                <span className="step">01</span>
                <h3>Notice your ground</h3>
                <p>
                  Two photographs and a little context can become a useful
                  scientific observation.
                </p>
              </section>
              <section className="field-card">
                <span className="step">02</span>
                <h3>Contribute with care</h3>
                <p>
                  Quality checks and private processing keep exact locations off
                  the public map.
                </p>
              </section>
              <section className="field-card">
                <span className="step">03</span>
                <h3>Build open knowledge</h3>
                <p>
                  Approved observations can join a licensed dataset that
                  researchers can inspect and reuse.
                </p>
              </section>
            </div>
          </>
        )}
        <div hidden={tab !== 'Capture'}>
          <section className="page-heading">
            <p className="eyebrow">YOUR FIELD NOTEBOOK</p>
            <h1>Help map the ground beneath us.</h1>
            <p>
              Your precise location stays private. Share the observation, not
              the exact pin.
            </p>
          </section>
          {!enabled ? (
            <section className="field-card">
              <h2>Capture is not open yet.</h2>
              <p>
                You can explore the map and learn the protocol while
                contribution intake is closed.
              </p>
              <button onClick={() => go('Learn')}>
                Explore the field guide
              </button>
            </section>
          ) : (
            <>
              {!client && (
                <p className="notice">
                  Local preview: observations stay on this device until a
                  contribution service is configured.
                </p>
              )}
              <CaptureForm
                key={formKey}
                initial={draft}
                onSave={save}
                saving={busy}
              />
            </>
          )}
        </div>
        {tab === 'Observations' && (
          <>
            <section className="page-heading">
              <p className="eyebrow">YOUR CONTRIBUTIONS</p>
              <h1>My observations.</h1>
              <p>A clear record, from the field to the map.</p>
            </section>
            <div className="action-row">
              <button
                className="secondary"
                disabled={syncing || !enabled || !client || !online}
                onClick={() =>
                  void retryDeadLettered().then(refresh).then(sync)
                }
              >
                {syncing
                  ? 'Syncing…'
                  : dead.length
                    ? 'Retry failed observations'
                    : 'Sync observations'}
              </button>
              <button
                className="text-button"
                onClick={() => void refreshRemote()}
              >
                Refresh status
              </button>
            </div>
            {records.length === 0 && remote.length === 0 && (
              <section className="empty-state">
                <Icon index={2} />
                <h2>Your field notebook starts here.</h2>
                <p>
                  Saved drafts and contributions will appear here. Each one adds
                  a little more understanding.
                </p>
                <button onClick={() => go('Capture')}>
                  Start an observation
                </button>
              </section>
            )}
            {records.map((r) => (
              <article className="observation" key={r.submissionId}>
                <div>
                  <span className="tag">
                    {r.draft
                      ? 'Draft · on this device'
                      : r.deadLetteredAt
                        ? 'Needs attention'
                        : 'Saved · waiting to upload'}
                  </span>
                  <h3>
                    {r.landCover || 'Field observation'} · {r.photos.length}{' '}
                    photos
                  </h3>
                  <p className="sample-reference">
                    Observation reference: <code>{r.submissionId}</code>
                  </p>
                  <p>
                    {new Date(r.capturedAt).toLocaleDateString()} ·{' '}
                    {r.draft
                      ? 'Finish the protocol before uploading.'
                      : 'Keep this app open to resume when connected.'}
                  </p>
                </div>
                <div className="action-row">
                  {r.draft && (
                    <button
                      className="secondary"
                      disabled={!enabled}
                      onClick={() => {
                        setDraft(r)
                        setFormKey(r.submissionId)
                        go('Capture')
                      }}
                    >
                      Resume draft
                    </button>
                  )}
                  <button
                    className="text-button"
                    disabled={syncing}
                    onClick={() => {
                      if (
                        window.confirm(
                          'Remove this observation from this device? Uploaded server data is not removed.',
                        )
                      )
                        void removeQueued(r.submissionId).then(refresh)
                    }}
                  >
                    Remove local copy
                  </button>
                </div>
              </article>
            ))}
            {remote
              .filter(
                (r) => !records.some((local) => local.submissionId === r.id),
              )
              .map((r) => (
                <button
                  className="observation remote"
                  key={r.id}
                  onClick={() => setDetail(r)}
                >
                  <span className="tag">{labelStatus(r)}</span>
                  <h3>{r.land_cover || 'Field observation'}</h3>
                  <p>
                    {new Date(r.captured_at).toLocaleDateString()} · View
                    details →
                  </p>
                </button>
              ))}
            {detail && (
              <section className="field-card detail">
                <button className="text-button" onClick={() => setDetail(null)}>
                  Close details
                </button>
                <h2>Observation detail</h2>
                <p>{labelStatus(detail)}</p>
                <p className="sample-reference">
                  Observation reference: <code>{detail.id}</code>
                </p>
                <p>
                  Approximate public cell:{' '}
                  {detail.h3_r8 ?? 'Available after quality review'}
                </p>
                <h3>Quality checks</h3>
                {detail.qa_events.length ? (
                  <ul>
                    {detail.qa_events.map((e) => (
                      <li key={e.check_name}>
                        {e.check_name.replaceAll('_', ' ')}:{' '}
                        {e.passed ? 'passed' : 'needs attention'}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>Quality results are not available yet.</p>
                )}
                <h3>Existing soil-map context</h3>
                {detail.priors.length ? (
                  <ul>
                    {detail.priors.map((p) => (
                      <li
                        key={`${p.source}-${p.property}-${p.depth_bottom_cm}`}
                      >
                        {p.property}: {p.value ?? 'unavailable'} {p.unit} ·{' '}
                        {p.depth_top_cm}–{p.depth_bottom_cm} cm · {p.source}
                        {p.uncertainty_lo !== null && p.uncertainty_hi !== null
                          ? ` · range ${p.uncertainty_lo}–${p.uncertainty_hi}`
                          : ' · uncertainty unavailable'}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>
                    Map priors are not available yet. No photo-based estimate
                    has been generated.
                  </p>
                )}
              </section>
            )}
          </>
        )}
        {tab === 'Learn' && (
          <>
            <section className="page-heading">
              <p className="eyebrow">THE FIELD GUIDE</p>
              <h1>
                A little care.
                <br />
                <em>Better observations.</em>
              </h1>
              <p>
                Everyone can contribute. A consistent method makes the
                observations more useful.
              </p>
            </section>
            <div className="intro-grid">
              <section className="field-card">
                <span className="step">01</span>
                <h2>Bring a reference.</h2>
                <p>
                  Print the A6 reference card at actual size. Include it in even
                  daylight without glare.
                </p>
                <button
                  className="secondary"
                  onClick={() =>
                    resource('/reference-card/gsip-reference-card-v1-color.pdf')
                  }
                >
                  Download color card
                </button>
                <button
                  className="text-button"
                  onClick={() =>
                    resource('/reference-card/gsip-reference-card-v1-bw.pdf')
                  }
                >
                  Black & white edition
                </button>
              </section>
              <section className="field-card">
                <span className="step">02</span>
                <h2>Capture the context.</h2>
                <p>
                  Photograph the undisturbed ground from around 30 cm. Gently
                  expose a fresh soil face and photograph it from around 15 cm.
                  Only sample where you have permission.
                </p>
              </section>
              <section className="field-card">
                <span className="step">03</span>
                <h2>Know what it means.</h2>
                <p>
                  Our first release collects observations and shows existing
                  soil-map estimates. Photographs do not replace laboratory
                  analysis. Validated models are future research.
                </p>
              </section>
            </div>
            <section
              className="field-card"
              aria-labelledby="prediction-research-title"
            >
              <span className="tag">Prediction research</span>
              <h2 id="prediction-research-title">
                From observations to estimates.
              </h2>
              <p>
                The next step combines existing soil maps, photo features, and
                laboratory measurements from the same sampled soil. We compare
                the combined model with the map alone using separate test
                locations.
              </p>
              <p>
                Image predictions are not available yet. Phone photos capture
                visible color and structure; they do not measure a full soil
                spectrum. Until a model is validated, map values remain labeled
                as existing soil-map context.
              </p>
              <p>
                Taking part in a lab-linked pilot? Keep the observation
                reference from My observations with your sample label, sampling
                depth, and laboratory report. A shared reference links the
                records; it does not verify the measurement.
              </p>
            </section>
            <section className="field-card">
              <h2>Open from the ground up.</h2>
              <p>
                Code: MIT. Structured data: ODbL 1.0. Contributed photos: CC
                BY-SA 4.0. Exact locations and account details stay private.
              </p>
              <button
                className="secondary"
                onClick={() =>
                  resource('https://github.com/global-soil-intelligence/gsip')
                }
              >
                View the open-source project
              </button>
            </section>
          </>
        )}
        {tab === 'Account' && (
          <>
            <section className="page-heading">
              <p className="eyebrow">YOUR IDENTITY, YOUR CHOICE</p>
              <h1>
                Contribute as yourself.
                <br />
                <em>Or a pseudonym.</em>
              </h1>
              <p>{account}</p>
            </section>
            <section className="field-card">
              <h2>Keep your observations connected.</h2>
              <p>
                Link an email to your anonymous account to preserve ownership.
                Open the verification link on this device.
              </p>
              <form
                onSubmit={(e) => {
                  e.preventDefault()
                  if (!client) return
                  setBusy(true)
                  void connectEmail(client, email)
                    .then((type) => {
                      setOtpType(type)
                      setSent(true)
                      setStatus(
                        'Check your email for the sign-in or verification link.',
                      )
                    })
                    .catch((e) =>
                      setError(
                        e instanceof Error
                          ? e.message
                          : 'Email could not be linked.',
                      ),
                    )
                    .finally(() => setBusy(false))
                }}
              >
                <label>
                  Email
                  <input
                    type="email"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </label>
                <button disabled={!client || busy}>Send secure link</button>
              </form>
              {!client && (
                <p className="hint">
                  Account services are unavailable in the local preview.
                </p>
              )}
              {sent && (
                <form
                  onSubmit={(e) => {
                    e.preventDefault()
                    if (!client) return
                    void client.auth
                      .verifyOtp({ email, token, type: otpType })
                      .then(({ error }) => {
                        if (error)
                          setError(
                            'The verification code was not accepted. Please request a new one.',
                          )
                        else {
                          setSent(false)
                          setStatus('Email verified.')
                          void refreshRemote()
                        }
                      })
                  }}
                >
                  <label>
                    Verification code, if included in your email
                    <input
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      value={token}
                      onChange={(e) => setToken(e.target.value)}
                      required
                    />
                  </label>
                  <button className="secondary">Verify code</button>
                </form>
              )}
            </section>
            <section className="field-card">
              <h2>Your privacy in the field.</h2>
              <p>
                Location is requested only when you add an observation. Original
                photos are uploaded privately and sanitized before publication.
                The public map uses approximate cells.
              </p>
              <p>
                You can remove drafts in My observations. Published data carries
                an open license; removing a local copy does not withdraw a
                public release.
              </p>
              <p>
                Account and data-removal requests must be handled before a
                public store launch. This development build does not yet offer
                account deletion.
              </p>
            </section>
          </>
        )}
        <div className="app-status" role="status">
          {status}
          {pending.length > 0 && (
            <span>
              {' '}
              ·{' '}
              {dead.length
                ? `${dead.length} needs attention`
                : `${pending.length} queued`}
            </span>
          )}
        </div>
        {error && (
          <div className="notice error" role="alert">
            {error}
            <button className="text-button" onClick={() => setError('')}>
              Dismiss
            </button>
          </div>
        )}
        <footer className="app-footer">
          A shared record of our living planet.
          <br />
          <span>Open science · Private locations · Honest uncertainty</span>
        </footer>
      </div>
      <nav className="bottom-nav" aria-label="Main navigation">
        {tabs.map((name, i) => (
          <button
            key={name}
            aria-current={tab === name ? 'page' : undefined}
            onClick={() => go(name)}
          >
            <Icon index={i} />
            <span>{name === 'Observations' ? 'My observations' : name}</span>
          </button>
        ))}
      </nav>
    </div>
  )
}
