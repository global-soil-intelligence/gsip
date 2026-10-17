import type { ReactNode } from 'react'

export type PageId = 'about' | 'card' | 'data' | 'home' | 'methods'

const repository = 'https://github.com/global-soil-intelligence/gsip'
const captureLive = import.meta.env.VITE_CAPTURE_LIVE === 'true'
const datasetUrl = import.meta.env.VITE_DATASET_URL?.trim()
// The deployed gsip-public function (WP-AGENT-1). Unset until it is live, so the site never
// advertises an interface that does not answer.
const publicApi = import.meta.env.VITE_GSIP_PUBLIC_API?.trim().replace(
  /\/+$/,
  '',
)
const agentGuide = `${repository}/blob/main/docs/AGENTS.md`
const libraryGuide = `${repository}/blob/main/docs/SOIL_LIBRARY.md`

export const PAGES: readonly PageId[] = [
  'home',
  'about',
  'card',
  'data',
  'methods',
]

export const pageMeta: Record<
  PageId,
  { description: string; eyebrow: string; title: string }
> = {
  about: {
    description:
      'Building an open soil spectral reference library with smartphone observations, instrument spectra and laboratory evidence.',
    eyebrow: 'The project',
    title: 'A shared library for the ground we depend on.',
  },
  card: {
    description:
      'No printed card is needed. Download the optional GSIP reference card and follow the phone-photo protocol.',
    eyebrow: 'An optional physical reference',
    title: 'Give every phone camera a reference point.',
  },
  data: {
    description:
      'Explore the soil library tools, planned public releases, licences and privacy boundaries.',
    eyebrow: 'Open data, honest boundaries',
    title: 'A dataset designed to be used—and scrutinized.',
  },
  home: {
    description:
      'An open soil spectral reference library in development: smartphone observations linked to instrument spectra and laboratory evidence.',
    eyebrow: 'Open science for the ground beneath us',
    title: 'Build the world’s open soil spectral library.',
  },
  methods: {
    description:
      'How phone images, measured spectra and laboratory evidence connect without overstating what they prove.',
    eyebrow: 'Methods in the open',
    title: 'Scientific honesty is part of the architecture.',
  },
}

/** Planned public releases, described without claiming measured spectral coverage. */
const datasetJsonLd = {
  '@id': 'https://globalsoilintelligence.com/data/#dataset',
  '@type': 'Dataset',
  name: 'GSIP soil library public releases',
  description:
    'Planned public releases from an open soil spectral reference library in development. Smartphone RGB images are not measured spectra; instrument spectra and verified laboratory evidence must be linked to the same physical samples. New releases contain structured data only until photo screening is deployed and its calibration approved; individual spectra remain private pending review. Public observation locations are k-anonymous H3 cells shared by at least 3 contributors, never precise points. Map priors are estimates, not laboratory results.',
  url: 'https://globalsoilintelligence.com/data/',
  // Two licences: the structured data and the photographs are licensed separately.
  license: [
    'https://opendatacommons.org/licenses/odbl/1-0/',
    'https://creativecommons.org/licenses/by-sa/4.0/',
  ],
  conditionsOfAccess:
    'Structured data under ODbL 1.0; contributed photographs under CC BY-SA 4.0, credited to their contributors.',
  isAccessibleForFree: true,
  creativeWorkStatus: 'In development; public releases gated',
  creator: { '@id': 'https://globalsoilintelligence.com/#organization' },
  publisher: { '@id': 'https://globalsoilintelligence.com/#organization' },
  keywords: [
    'soil',
    'citizen science',
    'soil photographs',
    'soil spectral library',
    'H3',
    'open data',
  ],
  measurementTechnique:
    'Smartphone RGB observations with an optional physical reference card; separately recorded instrument reflectance and laboratory methods, linked by physical sample identity',
  // The repository page, not a download: its files change with every release.
  ...(datasetUrl ? { sameAs: datasetUrl } : {}),
}

function pathFrom(page: PageId, path: string) {
  return `${page === 'home' ? './' : '../'}${path}`
}

function CaptureLink({
  className = 'button button-primary',
  page,
}: {
  className?: string
  page: PageId
}) {
  return (
    <a
      className={className}
      href={
        captureLive
          ? pathFrom(page, 'capture/')
          : pathFrom(page, 'about/#launch-status')
      }
    >
      {captureLive ? 'Contribute an observation' : 'Public capture closed'}
    </a>
  )
}

function Brand({ page }: { page: PageId }) {
  return (
    <a className="brand" href={pathFrom(page, '')}>
      <span className="brand-mark" aria-hidden="true">
        G
      </span>
      <span>
        Global Soil
        <br />
        Intelligence
      </span>
    </a>
  )
}

function Header({ page }: { page: PageId }) {
  return (
    <header className="site-header">
      <Brand page={page} />
      <nav aria-label="Primary navigation">
        <a href={pathFrom(page, 'map/')}>Map</a>
        <a href={pathFrom(page, 'data/')}>Library</a>
        <a href={pathFrom(page, 'methods/')}>Methods</a>
        <CaptureLink className="nav-cta" page={page} />
      </nav>
    </header>
  )
}

function Footer({ page }: { page: PageId }) {
  return (
    <footer className="site-footer">
      <div className="footer-lead">
        <Brand page={page} />
        <p>
          Building an open soil spectral library for future models and maps.
        </p>
      </div>
      <div className="footer-links">
        <div>
          <p className="footer-label">Explore</p>
          <a href={pathFrom(page, 'map/')}>Public map</a>
          <a href={pathFrom(page, 'card/')}>Reference card</a>
          <a href={pathFrom(page, 'data/')}>Open data</a>
        </div>
        <div>
          <p className="footer-label">Project</p>
          <a href={pathFrom(page, 'methods/')}>Methods</a>
          <a href={pathFrom(page, 'about/')}>About</a>
          <a href={repository}>Source code</a>
        </div>
      </div>
      <div className="footer-legal">
        <p>
          Code MIT · structured data ODbL 1.0 · contributed photos CC BY-SA 4.0
        </p>
        <p>
          GSIP is not a replacement for laboratory analysis. Estimates must
          carry uncertainty.
        </p>
      </div>
    </footer>
  )
}

function PageShell({ children, page }: { children: ReactNode; page: PageId }) {
  const meta = pageMeta[page]
  const canonical =
    page === 'home'
      ? 'https://globalsoilintelligence.com/'
      : `https://globalsoilintelligence.com/${page}/`
  const structuredData = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@id': 'https://globalsoilintelligence.com/#organization',
        '@type': 'Organization',
        name: 'Global Soil Intelligence',
        sameAs: [repository],
        url: 'https://globalsoilintelligence.com/',
      },
      {
        '@type': page === 'home' ? 'WebSite' : 'WebPage',
        description: meta.description,
        name:
          page === 'home'
            ? 'Global Soil Intelligence'
            : `${meta.title} — Global Soil Intelligence`,
        publisher: {
          '@id': 'https://globalsoilintelligence.com/#organization',
        },
        url: canonical,
      },
      ...(page === 'home' || page === 'data' ? [datasetJsonLd] : []),
    ],
  }
  return (
    <>
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <Header page={page} />
      {children}
      <Footer page={page} />
      <script
        type="application/ld+json"
        // Prerendered as raw script text: React would escape quotes in a text child. `<` is
        // escaped so the data can never close the script element.
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(structuredData).replace(/</g, '\\u003c'),
        }}
      />
    </>
  )
}

function SectionHeading({
  eyebrow,
  title,
}: {
  eyebrow: string
  title: string
}) {
  return (
    <div className="section-heading">
      <p className="eyebrow">{eyebrow}</p>
      <h2>{title}</h2>
    </div>
  )
}

function HomePage() {
  return (
    <PageShell page="home">
      <main id="main-content">
        <section className="home-hero">
          <div className="hero-copy">
            <p className="eyebrow">{pageMeta.home.eyebrow}</p>
            <h1>{pageMeta.home.title}</h1>
            <p className="hero-deck">
              We’re building a shared reference library that connects smartphone
              soil observations and sample metadata with instrument spectra and
              laboratory evidence from the same physical samples. Open AI models
              and better soil maps are the goal.
            </p>
            <div className="button-row">
              <a className="button button-primary" href={repository}>
                Build with GSIP
              </a>
              <a
                className="button button-secondary"
                href={`${libraryGuide}#run-the-complete-local-demo`}
              >
                Run the synthetic library demo
              </a>
            </div>
            <p className="hero-stage">
              In development. Public capture and library uploads remain closed.
            </p>
          </div>
          <div
            className="hero-visual"
            aria-label="The soil library’s evidence goal"
          >
            <div className="orbit orbit-one" aria-hidden="true" />
            <div className="orbit orbit-two" aria-hidden="true" />
            <div className="hero-visual-card visual-phone">
              <span>01</span>
              <strong>Phone observation</strong>
              <small>Images + field context</small>
            </div>
            <div className="hero-visual-card visual-cell">
              <span>02</span>
              <strong>Same soil sample</strong>
              <small>Instrument + lab evidence</small>
            </div>
            <div className="hero-visual-card visual-map">
              <span>03</span>
              <strong>Future open AI</strong>
              <small>Evaluate before mapping</small>
            </div>
          </div>
          <div className="trust-line">
            <span>Open source</span>
            <span>Precise locations stay private</span>
            <span>RGB ≠ measured spectra</span>
            <span>Uncertainty stays visible</span>
          </div>
        </section>

        <section className="section section-steps">
          <SectionHeading
            eyebrow="The evidence we’re building toward"
            title="A phone starts the record. Measurement builds the reference."
          />
          <ol className="steps-grid">
            {[
              [
                'Take two phone photos',
                'No printed card is needed. Capture context and a fresh-face close-up where you have permission to sample.',
                './about/#launch-status',
              ],
              [
                'Add context',
                'Record the place and surface condition. Library sample registration is optional and requires your real declared depth. Public capture is closed.',
                './methods/',
              ],
              [
                'Pair measurements',
                'Link instrument spectra and laboratory evidence to that same sample, with method and calibration records.',
                './methods/',
              ],
              [
                'Evaluate, then share',
                'Verify rights, pairing and quality before independent model evaluation or an eligible public release.',
                './data/',
              ],
            ].map(([title, description, href], index) => (
              <li key={title}>
                <span className="step-number">
                  {String(index + 1).padStart(2, '0')}
                </span>
                <h3>{title}</h3>
                <p>{description}</p>
                <a href={href}>Learn more</a>
              </li>
            ))}
          </ol>
        </section>

        <section className="section map-feature">
          <div className="map-copy">
            <p className="eyebrow">Open soil context</p>
            <h2>See the patterns. Never the private point.</h2>
            <p>
              The map is one way to use the library’s future evidence. Today it
              offers SoilGrids SOC, pH, and clay context, with a layer for
              eligible community coverage in H3 cells. These priors are
              estimates, not new measurements; deeper zoom never invents finer
              source resolution.
            </p>
            <a className="text-link" href="./map/">
              Open the global map <span aria-hidden="true">↗</span>
            </a>
          </div>
          <div className="map-motif" aria-label="Abstract privacy-safe H3 map">
            <div className="map-grid" aria-hidden="true">
              {Array.from({ length: 18 }, (_, index) => (
                <span key={index} className={`hex hex-${(index % 5) + 1}`} />
              ))}
            </div>
            <div className="map-key">
              <span>
                <i className="key-prior" /> Soil prior
              </span>
              <span>
                <i className="key-community" /> H3 coverage
              </span>
            </div>
          </div>
        </section>

        <section className="section card-feature">
          <div className="card-preview">
            <img
              src="./card-color-preview.png"
              alt="Preview of the printable GSIP color reference card"
              width="435"
              height="612"
            />
          </div>
          <div>
            <p className="eyebrow">A shared visual aid</p>
            <h2>An optional physical reference.</h2>
            <p>
              If you have the free physical reference card, include it for
              geometry and image checks. No printed card is needed. A card does
              not turn a phone into a spectrometer; phone photographs and any
              separately extracted soil RGB remain uncalibrated.
            </p>
            <div className="button-row">
              <a className="button button-primary" href="./card/">
                Optional reference card
              </a>
              <a
                className="button button-quiet"
                href="./reference-card/gsip-reference-card-v1-color.pdf"
              >
                Color PDF
              </a>
            </div>
          </div>
        </section>

        <section className="section data-flywheel">
          <SectionHeading
            eyebrow="From shared evidence to open models"
            title="Build the reference before trusting the prediction."
          />
          <div className="flow-row" aria-label="GSIP library research plan">
            {[
              ['Phone', 'Images + context'],
              ['Sample', 'Shared physical identity'],
              ['Measurement', 'Spectra + lab evidence'],
              ['Evaluation', 'Independent validation'],
              ['Future models', 'Open weights + maps'],
            ].map(([title, subtitle], index) => (
              <div className="flow-node" key={title}>
                <span>{String(index + 1).padStart(2, '0')}</span>
                <strong>{title}</strong>
                <small>{subtitle}</small>
              </div>
            ))}
          </div>
          <div className="dataset-status">
            <span className={datasetUrl ? 'status-live' : 'status-pending'} />
            <div>
              <strong>
                {datasetUrl
                  ? 'Public dataset destination'
                  : 'Public data releases remain gated'}
              </strong>
              <p>
                {datasetUrl
                  ? 'See the configured destination for its published release status and contents.'
                  : 'Code and local tools are available now. Public releases wait for rights, privacy, scientific and operator gates.'}
              </p>
            </div>
            {datasetUrl ? (
              <a href={datasetUrl}>Open dataset</a>
            ) : (
              <a href="./data/">Read the data plan</a>
            )}
          </div>
        </section>

        <section className="section privacy-feature">
          <div>
            <p className="eyebrow">Privacy by architecture</p>
            <h2>
              Sharing evidence starts with protecting the person behind it.
            </h2>
          </div>
          <div className="privacy-grid">
            <article>
              <span>01</span>
              <h3>Precise stays private</h3>
              <p>
                Exact coordinates support enrichment and QA inside protected
                infrastructure only.
              </p>
            </article>
            <article>
              <span>02</span>
              <h3>Metadata is stripped</h3>
              <p>
                The pipeline sanitizes embedded metadata. Photo publication
                stays held until screening is deployed and its calibration
                approved.
              </p>
            </article>
            <article>
              <span>03</span>
              <h3>Uncertainty is explicit</h3>
              <p>
                Public soil maps are priors, not truth. Future estimates must
                show their basis and confidence.
              </p>
            </article>
          </div>
          <a className="text-link light-link" href="./methods/">
            Read the complete method <span aria-hidden="true">→</span>
          </a>
        </section>

        <section className="section open-source-feature">
          <p className="eyebrow">Built in the open</p>
          <h2>The whole stack is open source.</h2>
          <p>
            The apps, backend, data pipeline, library tools, modelling code, API
            and reference-card generator are available in the public repository.
            Fork, run, modify and extend the MIT-licensed software, or build on
            one part of it.
          </p>
          <p>
            Run a private local library node with the public source. Your
            records and credentials remain protected. These tools do not
            register a node for GSIP’s hosted service; public uploads stay
            closed. We welcome developers, soil scientists and spectroscopy labs
            to help build verified paired evidence and future open models.
          </p>
          <div className="button-row">
            <a
              className="button button-primary"
              href={`${repository}#build-on-gsip`}
            >
              Explore the whole project
            </a>
            <a className="button button-secondary" href="./about/">
              About the project
            </a>
          </div>
        </section>
      </main>
    </PageShell>
  )
}

function InteriorHero({ page }: { page: Exclude<PageId, 'home'> }) {
  const meta = pageMeta[page]
  return (
    <section className="interior-hero">
      <p className="eyebrow">{meta.eyebrow}</p>
      <h1>{meta.title}</h1>
      <p>{meta.description}</p>
    </section>
  )
}

function CardPage() {
  return (
    <PageShell page="card">
      <main id="main-content">
        <InteriorHero page="card" />
        <section className="interior-section">
          <p>
            No printed card is needed. Photos A and B are required, and photo C
            is optional. If you choose the physical card, use the free downloads
            and printing instructions below. Missing a card alone never fails
            QA; every other quality, privacy and admission gate still applies.
          </p>
        </section>
        <section className="interior-section card-download-grid">
          <article className="download-card">
            <img
              src="../card-color-preview.png"
              alt="GSIP color reference card preview"
              width="435"
              height="612"
            />
            <div>
              <p className="eyebrow">Recommended</p>
              <h2>Color reference card</h2>
              <p>
                Nine documented patches, a neutral reference, and an ArUco
                marker support geometry and image checks. Soil RGB remains
                uncalibrated, even with the reference card.
              </p>
              <a
                className="button button-primary"
                href="../reference-card/gsip-reference-card-v1-color.pdf"
              >
                Download color PDF
              </a>
            </div>
          </article>
          <article className="download-card">
            <img
              src="../card-bw-preview.png"
              alt="GSIP black-and-white reference card preview"
              width="435"
              height="612"
            />
            <div>
              <p className="eyebrow">Geometry support</p>
              <h2>Black-and-white card</h2>
              <p>
                Use this edition when color printing is unavailable. It supports
                framing, scale, geometry, and exposure—not calibrated color
                recovery.
              </p>
              <a
                className="button button-secondary"
                href="../reference-card/gsip-reference-card-v1-bw.pdf"
              >
                Download B&amp;W PDF
              </a>
            </div>
          </article>
        </section>
        <section className="interior-section print-guide">
          <SectionHeading
            eyebrow="Print once, use outside"
            title="Keep the dimensions honest."
          />
          <div className="instruction-grid">
            <article>
              <span>01</span>
              <h3>Choose A6 paper</h3>
              <p>Use the document’s native A6 size or trim after printing.</p>
            </article>
            <article>
              <span>02</span>
              <h3>Print at 100%</h3>
              <p>Disable “fit to page” so the scale marker stays accurate.</p>
            </article>
            <article>
              <span>03</span>
              <h3>Keep it matte</h3>
              <p>Avoid glossy lamination that introduces glare outdoors.</p>
            </article>
          </div>
        </section>
        <section className="interior-section shot-guide">
          <SectionHeading
            eyebrow="Capture protocol"
            title="Two required photographs. One optional boost."
          />
          <div className="shot-grid">
            <article>
              <span>A</span>
              <h3>Context · required</h3>
              <p>
                Undisturbed ground surface from roughly 30 cm. Include the
                optional physical card if you have one.
              </p>
            </article>
            <article>
              <span>B</span>
              <h3>Fresh face · required</h3>
              <p>
                Scrape 2–3 cm, then photograph the exposed soil from roughly 15
                cm. Include the optional physical card if you have one.
              </p>
            </article>
            <article>
              <span>C</span>
              <h3>Texture · optional</h3>
              <p>
                A moistened soil ball or ribbon can improve future
                texture-confidence work.
              </p>
            </article>
          </div>
          <CaptureLink page="card" />
        </section>
      </main>
    </PageShell>
  )
}

function MethodsPage() {
  return (
    <PageShell page="methods">
      <main id="main-content">
        <InteriorHero page="methods" />
        <section className="interior-section">
          <SectionHeading
            eyebrow="Capture and release architecture"
            title="A fail-closed path from private capture to public context."
          />
          <div className="architecture-flow">
            {[
              [
                'Capture PWA',
                'Phone photos, optional card, context, private GPS',
              ],
              ['Private ingest', 'RLS, quarantine, immutable grant'],
              ['Prior enrichment', 'SoilGrids, SSURGO, Open-Meteo'],
              [
                'Deterministic QA',
                'Sanitize, sharpness, optional card, GPS, duplicate',
              ],
              [
                'Gated public release',
                'Eligible structured data; photos held pending screening',
              ],
            ].map(([title, detail], index) => (
              <article key={title}>
                <span>{String(index + 1).padStart(2, '0')}</span>
                <h3>{title}</h3>
                <p>{detail}</p>
              </article>
            ))}
          </div>
        </section>
        <section className="interior-section">
          <SectionHeading
            eyebrow="Different evidence, connected by one sample"
            title="A photograph is an observation. A spectrum is a measurement."
          />
          <div className="instruction-grid">
            <article>
              <h3>Phone images</h3>
              <p>
                Ordinary phones record RGB images, not wavelength-resolved
                spectra. Extracted soil RGB is uncalibrated, even with the
                reference card. No printed card is needed. A photograph does not
                automatically create an extracted optical record or register a
                library sample. Sample registration is optional and needs your
                real declared depth.
              </p>
            </article>
            <article>
              <h3>Measured spectra</h3>
              <p>
                A separate instrument records reflectance by wavelength. Pairing
                it with the same physical sample requires verified identity,
                method, calibration and uncertainty.
              </p>
            </article>
            <article>
              <h3>Laboratory evidence</h3>
              <p>
                Verified assays provide separate reference labels. Biological
                relationships require actual assays and expert-reviewed terms;
                images or spectra alone do not establish soil microbial
                composition.
              </p>
            </article>
          </div>
          <p>
            The local RGB-to-reflectance demo uses invented samples and spectra.
            It demonstrates the software, not field accuracy. No independently
            validated soil reconstruction model is provided; real models need
            verified field pairs and independent spatial and device evaluation.
          </p>
        </section>
        <section className="interior-section split-section">
          <div>
            <p className="eyebrow">Existing maps are priors</p>
            <h2>Context helps. It does not get the final word.</h2>
          </div>
          <div className="prose-stack">
            <p>
              SoilGrids provides global soil context. SSURGO adds
              higher-resolution United States context. Open-Meteo contributes
              elevation and recent precipitation. These sources are stored as
              weak labels with uncertainty rather than treated as measured
              truth.
            </p>
            <p>
              Confirmed laboratory measurements are modeled separately as gold
              labels. Future estimators must report a basis and confidence
              interval for every output.
            </p>
          </div>
        </section>
        <section className="interior-section qa-section">
          <SectionHeading
            eyebrow="Deterministic photo QA"
            title="Quality checks are built; photo publication stays gated."
          />
          <div className="qa-grid">
            {[
              [
                'Metadata strip',
                'Orientation and colour profiles are applied to the pixels, then EXIF, GPS, XMP, ICC, comments, and residual segments are removed.',
              ],
              [
                'Image quality',
                'Sharpness and exposure are checked on the candidate soil region. A detected physical card is masked out; without one, the candidate region is the whole frame.',
              ],
              [
                'Optional reference card',
                'Missing a card alone never fails QA. Marker and patch extraction support geometry and image checks, not calibrated reflectance.',
              ],
              [
                'GPS plausibility',
                'Accuracy and gross prior mismatches can trigger review.',
              ],
              [
                'Duplicate defense',
                'Perceptual hashes flag repeated or near-repeated images.',
              ],
              [
                'Terminal outcome',
                'Each submission settles to pass, fail, or flagged review from its two required photos.',
              ],
            ].map(([title, detail]) => (
              <article key={title}>
                <h3>{title}</h3>
                <p>{detail}</p>
              </article>
            ))}
          </div>
        </section>
        <section className="interior-section privacy-method">
          <div>
            <p className="eyebrow">Public by design, private by default</p>
            <h2>Every public cell holds at least three contributors.</h2>
          </div>
          <div>
            <p>
              Exact geometry remains protected operational data. Public map and
              dataset records carry only H3 cells: resolution 8 (about 0.74 km²)
              where at least three people have contributed, otherwise the
              coarser resolution 6 or 4 cell. Anonymous public reads are limited
              to aggregate cells—not per-submission coordinates.
            </p>
            <a
              className="text-link"
              href={`${repository}/blob/main/docs/SPEC.md`}
            >
              Read the governing specification ↗
            </a>
            <br />
            <a
              className="text-link"
              href={`${repository}/blob/main/docs/BUILD_ORDER.md`}
            >
              Review the acceptance plan ↗
            </a>
          </div>
        </section>
      </main>
    </PageShell>
  )
}

function DataPage() {
  return (
    <PageShell page="data">
      <main id="main-content">
        <InteriorHero page="data" />
        <section className="interior-section release-status">
          <div className="release-badge">
            <span className={datasetUrl ? 'status-live' : 'status-pending'} />
            {datasetUrl ? 'Release destination configured' : 'Pre-publication'}
          </div>
          <div>
            <h2>
              {datasetUrl
                ? 'Check the public destination for release contents.'
                : 'Public data releases remain gated.'}
            </h2>
            <p>
              The release job fails closed if a contribution lacks its immutable
              grant, contains a precise location field, or carries embedded
              image metadata. New releases contain structured data only until
              photo screening is deployed and its calibration approved.
            </p>
            <p>
              Individual spectra remain private pending a fingerprinting and
              privacy review, even without coordinates. An H3 cell alone does
              not make a spectrum safe to publish.
            </p>
            {datasetUrl ? (
              <a className="button button-primary" href={datasetUrl}>
                Open on Hugging Face
              </a>
            ) : (
              <a className="button button-secondary" href={repository}>
                Inspect the export source
              </a>
            )}
          </div>
        </section>
        <section className="interior-section license-grid">
          <article>
            <p className="license-code">MIT</p>
            <h2>Source code</h2>
            <p>
              All GSIP software source is public: apps, backend, workers,
              library, modelling tools, API and tests. Use, modify, self-host or
              extend it under MIT. Dependencies retain their own licences.
            </p>
          </article>
          <article>
            <p className="license-code">ODbL 1.0</p>
            <h2>Structured data</h2>
            <p>
              Public database records use an open share-alike data license with
              source attribution.
            </p>
          </article>
          <article>
            <p className="license-code">CC BY-SA 4.0</p>
            <h2>Contributed photos</h2>
            <p>
              Contributors retain ownership and grant publication under a
              separate photo license with recorded attribution.
            </p>
          </article>
        </section>
        <section className="interior-section schema-section">
          <SectionHeading
            eyebrow="Public release boundary"
            title="Useful fields in. Sensitive fields out."
          />
          <div className="boundary-grid">
            <div>
              <h3>Eligible structured release fields</h3>
              <ul>
                <li>k-anonymous H3 cells (resolution 8, 6 or 4)</li>
                <li>Date-truncated capture time</li>
                <li>Protocol context and per-photo QA checks</li>
                <li>
                  Verified, rights-eligible labels outside sealed holdouts
                </li>
                <li>Provenance tier and published licence terms</li>
              </ul>
            </div>
            <div>
              <h3>Never public</h3>
              <ul>
                <li>Precise geometry or GPS accuracy</li>
                <li>Point-level soil-map priors, which pinpoint location</li>
                <li>Contributor or grant identifiers</li>
                <li>Device model or private camera fields</li>
                <li>Raw uploads or embedded metadata</li>
                <li>Private worker and queue state</li>
              </ul>
            </div>
          </div>
        </section>
        <section className="interior-section citation-section">
          <p className="eyebrow">Citation and takedown</p>
          <h2>Publication must be traceable. Withdrawal has limits.</h2>
          <p>
            The generated dataset card carries source citations, schema, license
            boundaries, photo attribution, and export-date provenance. A public
            privacy contact will be published before real contributions are
            released. Copies already released may persist; withdrawal removes
            eligibility from future GSIP releases and requires affected
            artifacts to be rebuilt. Do not post private contributor details in
            public issues.
          </p>
        </section>
        <section className="interior-section citation-section">
          <p className="eyebrow">Build on the library</p>
          <h2>Start locally. Keep evidence and authority separate.</h2>
          <p>
            The private local store accepts typed camera RGB and instrument
            reflectance records linked by sample identity. Local declarations
            are not verified GSIP acceptance. Hosted uploads, node exchange and
            public spectral releases remain gated.
          </p>
          <a className="text-link" href={libraryGuide}>
            Library developer guide ↗
          </a>
        </section>
        <section className="interior-section citation-section" id="agents">
          <p className="eyebrow">Agents and developers</p>
          <h2>Read the commons from code or an AI agent.</h2>
          <p>
            The read-only API and MCP server are designed for the capture
            protocol, eligible public cells and release metadata, with licences
            and citations. Configured endpoints appear below. They expose no
            precise locations or private library records, and offer no capture
            or node-registration tool.
          </p>
          <p className="agent-links">
            <a href={agentGuide}>Agent guide</a>
            {publicApi ? (
              <>
                {' · '}
                <a href={`${publicApi}/v1/openapi.json`}>OpenAPI description</a>
                {' · MCP endpoint '}
                <code>{`${publicApi}/mcp`}</code>
              </>
            ) : null}
          </p>
        </section>
      </main>
    </PageShell>
  )
}

function AboutPage() {
  return (
    <PageShell page="about">
      <main id="main-content">
        <InteriorHero page="about" />
        <section className="interior-section mission-block">
          <p className="eyebrow">The thesis</p>
          <h2>Make soil evidence easier to collect, connect and build on.</h2>
          <p>
            Smartphones are the accessible capture tool: images, field context
            and physical sample links. Instrument spectra and verified
            laboratory measurements supply reference evidence. GSIP aims to
            connect them in an open library for researchers, communities and AI
            builders, with soil maps as a downstream use. Understanding the soil
            biome also requires biological measurements; a phone photo cannot
            provide them.
          </p>
        </section>
        <section className="interior-section launch-status" id="launch-status">
          <div className="release-badge">
            <span className={captureLive ? 'status-live' : 'status-pending'} />
            In development
          </div>
          <div>
            <h2>
              {captureLive
                ? 'Public capture is open.'
                : 'Open source now. Public capture remains closed.'}
            </h2>
            <p>
              {captureLive
                ? 'The reviewed privacy, legal, authentication, and worker gates are active.'
                : 'Library uploads remain closed too. Opening them requires reviewed legal terms, privacy screening, scientific checks and a separate operator decision after the launch gates pass. No opening date is promised.'}
            </p>
          </div>
        </section>
        <section className="interior-section roadmap-section">
          <SectionHeading
            eyebrow="Roadmap"
            title="Build the evidence plane before the prediction layer."
          />
          <div className="roadmap-grid">
            <article>
              <span>Now</span>
              <h3>Local library tools</h3>
              <p>
                Typed measurement records, a private local store, staged optical
                extraction and a synthetic paired-model demo. Public source and
                build instructions are available now.
              </p>
            </article>
            <article>
              <span>Next</span>
              <h3>Verified paired evidence</h3>
              <p>
                Field samples paired with calibrated instruments and laboratory
                evidence, rights verification, privacy review and independent
                evaluation before scientific or publication claims.
              </p>
            </article>
            <article>
              <span>Future</span>
              <h3>Open models and soil maps</h3>
              <p>
                Train and evaluate models on eligible evidence, publish their
                limits and uncertainty, and use validated outputs to inform maps
                and further research.
              </p>
            </article>
          </div>
        </section>
        <section className="interior-section maintainer-block">
          <div>
            <p className="eyebrow">Open-source stewardship</p>
            <h2>Built by Viridis LLC with the work visible in public.</h2>
          </div>
          <div>
            <p>
              Justin Hart is the GSIP product owner. Architecture,
              implementation work packages, acceptance criteria, review
              findings, and source code are maintained in the public repository.
            </p>
            <div className="button-row">
              <a className="button button-primary" href={repository}>
                Open the repository
              </a>
              <a
                className="button button-secondary"
                href={`${repository}/issues`}
              >
                View open issues
              </a>
            </div>
          </div>
        </section>
      </main>
    </PageShell>
  )
}

export function App({ page }: { page: PageId }) {
  switch (page) {
    case 'about':
      return <AboutPage />
    case 'card':
      return <CardPage />
    case 'data':
      return <DataPage />
    case 'methods':
      return <MethodsPage />
    default:
      return <HomePage />
  }
}
