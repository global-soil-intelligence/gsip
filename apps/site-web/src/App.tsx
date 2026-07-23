import type { ReactNode } from 'react'

export type PageId = 'about' | 'card' | 'data' | 'home' | 'methods'

const repository = 'https://github.com/global-soil-intelligence/gsip'
const captureLive = import.meta.env.VITE_CAPTURE_LIVE === 'true'
const datasetUrl = import.meta.env.VITE_DATASET_URL?.trim()

const pageMeta: Record<
  PageId,
  { description: string; eyebrow: string; title: string }
> = {
  about: {
    description:
      'The mission, roadmap, and open-source community behind Global Soil Intelligence.',
    eyebrow: 'The project',
    title: 'A shared map for the ground we depend on.',
  },
  card: {
    description:
      'Print the GSIP reference card and follow the standard soil photography protocol.',
    eyebrow: 'A common visual standard',
    title: 'Give every phone camera a reference point.',
  },
  data: {
    description:
      'GSIP public dataset scope, licensing, citation, and publication status.',
    eyebrow: 'Open data, honest boundaries',
    title: 'A dataset designed to be used—and scrutinized.',
  },
  home: {
    description:
      'Photograph soil with your phone and help build a privacy-safe, open global soil dataset.',
    eyebrow: 'Open citizen science for the ground beneath us',
    title: 'Build the world’s living soil map.',
  },
  methods: {
    description:
      'How GSIP captures, sanitizes, grades, enriches, and publishes soil observations.',
    eyebrow: 'Methods in the open',
    title: 'Scientific honesty is part of the architecture.',
  },
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
      {captureLive ? 'Contribute an observation' : 'Capture opening soon'}
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
        <a href={pathFrom(page, 'card/')}>Print card</a>
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
        <p>Open infrastructure for a living, privacy-safe global soil map.</p>
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
      <script type="application/ld+json">
        {JSON.stringify(structuredData)}
      </script>
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
              Photograph soil with your phone. Contribute a privacy-safe
              observation. Help improve an open global dataset for researchers,
              communities, and the land.
            </p>
            <div className="button-row">
              <CaptureLink page="home" />
              <a className="button button-secondary" href="./map/">
                Explore the map
              </a>
            </div>
          </div>
          <div className="hero-visual" aria-label="GSIP observation flow">
            <div className="orbit orbit-one" aria-hidden="true" />
            <div className="orbit orbit-two" aria-hidden="true" />
            <div className="hero-visual-card visual-phone">
              <span>01</span>
              <strong>Phone observation</strong>
              <small>Two guided soil photos</small>
            </div>
            <div className="hero-visual-card visual-cell">
              <span>08</span>
              <strong>Private → H3</strong>
              <small>No precise public point</small>
            </div>
            <div className="hero-visual-card visual-map">
              <span>∞</span>
              <strong>Open soil context</strong>
              <small>A map that improves over time</small>
            </div>
          </div>
          <div className="trust-line">
            <span>Open source</span>
            <span>Precise locations stay private</span>
            <span>Photo metadata is stripped</span>
            <span>Uncertainty stays visible</span>
          </div>
        </section>

        <section className="section section-steps">
          <SectionHeading
            eyebrow="One observation, four safeguards"
            title="Simple in the field. Deliberate underneath."
          />
          <ol className="steps-grid">
            {[
              [
                'Print the card',
                'Use the free A6 reference to standardize scale, lighting, and color.',
                './card/',
              ],
              [
                'Photograph the soil',
                'Capture the ground surface and a fresh face. A texture shot is optional.',
                captureLive ? './capture/' : './about/#launch-status',
              ],
              [
                'Share privately',
                'Precise coordinates support QA and priors but never enter a public artifact.',
                './methods/',
              ],
              [
                'Publish safely',
                'The private pipeline strips metadata, grades quality, and releases H3-level output.',
                './methods/',
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
              Explore SoilGrids SOC, pH, and clay priors beside community
              coverage aggregated into H3 cells. Existing maps are context—not
              truth—and deeper zoom never invents finer source resolution.
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
            <p className="eyebrow">A shared visual standard</p>
            <h2>One card. Any modern phone.</h2>
            <p>
              The free reference card gives every image a common scale, exposure
              target, marker, and color reference. Print it at home, take it
              outside, and keep it beside the soil.
            </p>
            <div className="button-row">
              <a className="button button-primary" href="./card/">
                Print the reference card
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
            eyebrow="The open data flywheel"
            title="Every safe contribution makes the next map better."
          />
          <div className="flow-row" aria-label="GSIP Phase 1 data flow">
            {[
              ['Phone', 'Guided observation'],
              ['Private ingest', 'Supabase + RLS'],
              ['Deterministic QA', 'Sanitize + grade'],
              ['Open dataset', 'H3-safe release'],
              ['Future models', 'Open weights'],
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
                  ? 'Public dataset available'
                  : 'Public dataset preparing for launch'}
              </strong>
              <p>
                {datasetUrl
                  ? 'The latest privacy-checked release is available on Hugging Face.'
                  : 'The export pipeline is built. Publication waits for the reviewed destination and launch credentials.'}
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
              The useful signal becomes public. Your exact location does not.
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
                Photos are re-encoded and scanned at ingest and again before any
                public export.
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
          <h2>
            The code, methods, and public artifacts are designed to travel.
          </h2>
          <p>
            GSIP is open infrastructure: MIT-licensed code, ODbL structured
            data, separately licensed contributed photos, and future open model
            weights. Review the architecture, reproduce the pipeline, or help
            improve the next release.
          </p>
          <div className="button-row">
            <a className="button button-primary" href={repository}>
              View the source
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
                marker support scale, perspective, exposure, and color
                correction.
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
              <h3>Context</h3>
              <p>
                Undisturbed ground surface from roughly 30 cm, card visible.
              </p>
            </article>
            <article>
              <span>B</span>
              <h3>Fresh face</h3>
              <p>
                Scrape 2–3 cm, then photograph the exposed soil from roughly 15
                cm.
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
            eyebrow="Phase 1 architecture"
            title="A fail-closed path from private capture to public context."
          />
          <div className="architecture-flow">
            {[
              ['Capture PWA', 'Photos, protocol context, private GPS'],
              ['Private ingest', 'RLS, quarantine, immutable grant'],
              ['Prior enrichment', 'SoilGrids, SSURGO, Open-Meteo'],
              ['Deterministic QA', 'Sanitize, sharpness, card, GPS, duplicate'],
              ['Public release', 'H3 cells, safe metadata, licensed photos'],
            ].map(([title, detail], index) => (
              <article key={title}>
                <span>{String(index + 1).padStart(2, '0')}</span>
                <h3>{title}</h3>
                <p>{detail}</p>
              </article>
            ))}
          </div>
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
            title="The gate is live before the first model."
          />
          <div className="qa-grid">
            {[
              [
                'Metadata strip',
                'EXIF, GPS, XMP, ICC, comments, and residual application segments.',
              ],
              [
                'Image quality',
                'Sharpness and exposure thresholds grade usable signal.',
              ],
              [
                'Reference card',
                'Marker and patch extraction record calibration quality.',
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
                'Each submission reaches pass, fail, or flagged review state.',
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
            <h2>H3 resolution 8 is the public location boundary.</h2>
          </div>
          <div>
            <p>
              Exact geometry remains protected operational data. Public map and
              dataset records carry only H3 cells, and anonymous public reads
              are limited to aggregate cells—not per-submission coordinates.
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
            {datasetUrl ? 'Published' : 'Pre-publication'}
          </div>
          <div>
            <h2>
              {datasetUrl
                ? 'The privacy-checked public dataset is available.'
                : 'The export is built. The public repository is not live yet.'}
            </h2>
            <p>
              The release job fails closed if a contribution lacks its immutable
              grant, contains a precise location field, or carries embedded
              image metadata.
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
              The applications, pipeline, schema package, and supporting tools
              are open for use and self-hosting.
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
              <h3>Public</h3>
              <ul>
                <li>H3 resolution 8 and 6 cells</li>
                <li>Date-truncated capture time</li>
                <li>Protocol context and QA scores</li>
                <li>Weak priors and gold labels</li>
                <li>Sanitized photos with attribution</li>
              </ul>
            </div>
            <div>
              <h3>Never public</h3>
              <ul>
                <li>Precise geometry or GPS accuracy</li>
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
          <h2>Publication must remain traceable and reversible.</h2>
          <p>
            The generated dataset card carries source citations, schema, license
            boundaries, photo attribution, and export-date provenance. A public
            contact and repository issue path will be published before real
            contributions are released.
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
          <h2>
            A common protocol can turn millions of ordinary cameras into a
            shared observation network.
          </h2>
          <p>
            Global Soil Intelligence applies the citizen-science flywheel to
            soil: make contribution simple, protect the contributor, grade the
            observation, publish useful open artifacts, and improve the system
            as real evidence accumulates.
          </p>
        </section>
        <section className="interior-section launch-status" id="launch-status">
          <div className="release-badge">
            <span className={captureLive ? 'status-live' : 'status-pending'} />
            Phase 1
          </div>
          <div>
            <h2>
              {captureLive
                ? 'Public capture is open.'
                : 'The public hub and map can launch before contribution writes.'}
            </h2>
            <p>
              {captureLive
                ? 'The reviewed privacy, legal, authentication, and worker gates are active.'
                : 'The capture application is built and tested. It remains visibly closed until contribution terms receive legal review and production authentication and workers are configured.'}
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
              <h3>Phase 1 · Capture + map</h3>
              <p>
                Reference card, offline contribution, priors, deterministic QA,
                privacy-safe map, and public export.
              </p>
            </article>
            <article>
              <span>Next</span>
              <h3>Phase 2 · Open estimation</h3>
              <p>
                Soil-image QA, uncertainty-aware property estimation, model
                cards, and gold-label calibration.
              </p>
            </article>
            <article>
              <span>Future</span>
              <h3>Learning map</h3>
              <p>
                Fused correction layers, active-learning targets, on-device
                inference, and wider research participation.
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
