# GSIP public website — build specification

**Project:** Global Soil Intelligence Project

**Domain:** `globalsoilintelligence.com`

**Version:** 1.0 — 2026-07-23

**Status:** APPROVED FOR BUILD

**Owner:** Justin Hart, Viridis LLC

**Work package:** WP-SITE-1 — Phase 1 launch fast-follow

**Baseline:** `docs/SPEC.md` v2.2, `docs/BUILD_ORDER.md` v2.2, and the completed
WP-0 through WP-6 stack

## 1. Outcome

Build a fast, accessible public project hub at `https://globalsoilintelligence.com` that explains
GSIP, establishes trust, and routes visitors into the already-built capture and map applications.
The website is a launch surface for the Phase 1 system, not a new product or a replacement for the
capture PWA.

The primary conversion is:

> **Contribute a soil observation**

The secondary conversion is:

> **Explore the soil map**

The public site must accurately distinguish what is available in Phase 1 from future ML estimates.
It must not imply that a phone photo is a laboratory result or that the Phase 2 estimator is live.

## 2. Scope boundary

WP-SITE-1 is a separate pull request stacked after WP-6. It does not modify the database schema,
capture protocol, contribution licenses, QA thresholds, or public-export privacy rules.

### In scope

- A new TypeScript/Vite/React app at `apps/site-web`.
- A branded homepage and five supporting information pages.
- Integration with the existing `/capture/`, `/map/`, and `/reference-card/` artifacts.
- SEO, social-sharing metadata, sitemap, robots file, favicon, and a social preview image.
- GitHub Pages packaging at the site root.
- `globalsoilintelligence.com` and `www.globalsoilintelligence.com` DNS configuration.
- Accessibility, responsive design, performance, link, language, and browser acceptance tests.
- Honest launch-state messaging when the dataset or contribution service is unavailable.

### Out of scope

- Phase 2 ML, soil-property predictions, inference APIs, accounts dashboards, payments, analytics,
  advertising, newsletters, a CMS, a blog, or a second hosting provider.
- Fabricated map cells, contribution counts, testimonials, partner logos, or model results.
- Enabling anonymous production capture before the legal/privacy launch gate is signed off.
- Publishing the Hugging Face dataset before its repository, token, and takedown process exist.

## 3. URL and navigation architecture

| URL         | Purpose                                                           | Primary action              |
| ----------- | ----------------------------------------------------------------- | --------------------------- |
| `/`         | Mission, trust, system overview, and entry points                 | Contribute an observation   |
| `/capture/` | Existing offline-first capture PWA                                | Start the capture protocol  |
| `/map/`     | Existing privacy-safe MapLibre soil map                           | Explore soil context        |
| `/card/`    | Reference-card explanation and print guidance                     | Download color or B&W PDF   |
| `/methods/` | Capture protocol, data sources, QA, uncertainty, and privacy      | Read the open specification |
| `/data/`    | Dataset scope, licenses, schema, publication status, and citation | Open the dataset when live  |
| `/about/`   | Mission, open-source model, roadmap, contributors, and repository | View the source code        |

The existing PDF files remain available at:

- `/reference-card/gsip-reference-card-v1-color.pdf`
- `/reference-card/gsip-reference-card-v1-bw.pdf`

Every page uses the same compact header:

- Global Soil Intelligence wordmark → `/`
- Explore map → `/map/`
- Print card → `/card/`
- Methods → `/methods/`
- Primary button → `/capture/`

The footer includes the code repository, data and photo licenses, privacy summary, current project
phase, and a clear statement that GSIP is not a laboratory-test replacement.

## 4. Homepage content

### 4.1 Hero

**Eyebrow:** Open citizen science for the ground beneath us

**Headline:** Build the world’s living soil map.

**Body:** Photograph soil with your phone. Contribute a privacy-safe observation. Help improve an
open global dataset for researchers, communities, and the land.

**Primary CTA:** Contribute an observation

**Secondary CTA:** Explore the map

Trust line:

> Open source · Precise locations stay private · Photo metadata is stripped · Estimates carry
> uncertainty

Do not claim that GSIP currently predicts SOC, pH, CEC, nitrogen, or texture from images. The Phase
1 map shows existing soil priors and community coverage.

### 4.2 How one observation works

Use a four-step horizontal sequence on desktop and vertical sequence on mobile:

1. Print or open the reference-card guide.
2. Photograph the ground surface and a fresh soil face.
3. Share a location privately and accept the contribution licenses.
4. The private QA pipeline sanitizes, grades, and publishes only safe H3-level output.

Each step links to either `/card/`, `/capture/`, or `/methods/`.

### 4.3 Explore the map

Use a lightweight visual card rather than loading MapLibre on the homepage. The card explains:

- SOC, pH, and clay layers are public-map priors, not ground truth.
- Community coverage is displayed as privacy-safe H3 cells.
- No precise contributor point is shown.

The card links to `/map/`. It must never render synthetic contribution cells as live observations.

### 4.4 Reference card

Show a rendered preview of the committed A6 color card and explain why it improves scale, lighting,
and color consistency. Provide distinct download buttons:

- Download color card
- Download black-and-white card

The B&W card must be described as geometry/exposure support, not color calibration.

### 4.5 Open data flywheel

Explain the Phase 1 flow:

`phone → private Supabase ingest → deterministic QA → H3-safe public dataset → future open models`

Display the dataset state from a static build-time flag:

- `Not yet published` before a Hub destination exists.
- `Available on Hugging Face` only after the public repository is verified.

Do not display a row count unless it comes from the published dataset or the privacy-safe `h3_cells`
aggregate.

### 4.6 Privacy and scientific honesty

This section must state:

- Precise coordinates remain private operational data.
- Public locations are reduced to H3 resolution 8.
- Original uploads are quarantined; canonical and exported photos are metadata-sanitized.
- Existing soil maps are priors, not truth.
- GSIP outputs are probabilistic estimates with uncertainty.
- A GSIP estimate is not a substitute for laboratory analysis.

### 4.7 Open-source participation

Link to the GitHub repository, governing specification, contribution guide, issue tracker, and
future Hugging Face organization. Do not collect email addresses in v1.

## 5. Supporting page requirements

### `/card/`

- Card purpose and limitations.
- Shot A, B, and optional C instructions.
- Color and B&W PDF previews and downloads.
- A6, 100% scale, no “fit to page,” and consumer-printer guidance.
- Link directly to capture after printing.

### `/methods/`

- Phase 1 architecture diagram.
- Capture protocol and metadata allowlist.
- SoilGrids, SSURGO, Open-Meteo, and future WoSIS roles.
- Deterministic QA checks and terminal statuses.
- H3 privacy model and metadata stripping.
- Weak labels versus gold labels.
- Uncertainty and “not a laboratory result” language.
- Direct links to `SPEC.md`, `BUILD_ORDER.md`, and source code.

### `/data/`

- Publication state and last successful export date when available.
- Separate MIT code, ODbL structured-data, and CC BY-SA photo-license explanations.
- Public schema, citation block, and takedown contact path.
- Hugging Face link only after the repository exists.
- No private schema fields, precise coordinates, device models, grant identifiers, or camera
  metadata.

### `/about/`

- Mission and citizen-science thesis.
- Phase 1 / Phase 2 / future roadmap with no promised dates.
- Maintainer and contributor acknowledgements.
- Open-source repository and participation links.
- No invented institutional partnerships.

## 6. Visual system

Use the established GSIP visual language from the capture and map apps.

| Token           | Value     | Use                            |
| --------------- | --------- | ------------------------------ |
| Deep soil green | `#10251f` | Headers, footer, dark sections |
| Forest green    | `#18362b` | Text and primary controls      |
| Parchment       | `#f4f0e4` | Main background                |
| Lichen          | `#d8e7ad` | Primary CTA and highlights     |
| Ochre           | `#bd7531` | Secondary accents and status   |
| Terracotta      | `#cf4d3f` | Warnings only                  |
| Ink-muted       | `#53645c` | Supporting copy                |

- Editorial serif headlines with clean sans-serif body copy and restrained monospace labels.
- Self-host any non-system font as a licensed, subset WOFF2 asset; no remote font requests.
- Rounded panels, fine borders, topographic/H3 line motifs, card imagery, and map-derived color.
- Avoid generic agriculture stock photography, glossy AI imagery, fake dashboards, neon gradients,
  and decorative animation that slows the page.
- Motion is optional, subtle, and disabled by `prefers-reduced-motion`.
- All final imagery must have a documented source/license and meaningful alt text where needed.

## 7. Technical implementation

### Application

- Add `apps/site-web` as a pnpm workspace package.
- Use React, TypeScript strict mode, and Vite to match the current monorepo.
- Use Vite multi-page inputs for `/`, `/card/`, `/methods/`, `/data/`, and `/about/`.
- Share header, footer, page shell, CTA, status, and license components.
- Do not add a runtime router or CMS.
- Treat the site as static by default. The only optional client fetch is a privacy-safe aggregate
  status; failure must render “currently unavailable,” never invented data.

### Pages packaging

Update `scripts/build-pages.mjs`:

1. Copy `apps/site-web/dist/` into `_site/`.
2. Copy the capture build into `_site/capture/`.
3. Copy the map build into `_site/map/`.
4. Copy PDFs into `_site/reference-card/`.
5. Remove the current root meta-refresh redirect.

Because the repository publishes with a custom GitHub Actions workflow, the domain is configured in
GitHub Pages settings; a repository `CNAME` file is not required.

### Metadata

Every public page requires:

- Unique title and description.
- Canonical URL on `https://globalsoilintelligence.com`.
- Open Graph and social-card metadata.
- Favicon and theme color.
- Correct heading hierarchy.
- `robots.txt` and `sitemap.xml`.
- JSON-LD `WebSite` and `Organization` data with only verified public facts.

### Security and privacy

- No analytics, cookies, trackers, advertising pixels, session replay, or third-party embeds in v1.
- No service-role key or other server secret in the site bundle.
- No precise coordinates in URLs, DOM, logs, analytics, examples, or public assets.
- All external links use HTTPS.
- External links opened in a new tab use `rel="noopener noreferrer"`.
- The site must not weaken existing Supabase RLS, photo sanitization, export, or license gates.

## 8. Custom-domain deployment

Canonical domain: `globalsoilintelligence.com`. Configure `www.globalsoilintelligence.com` as the
redirecting companion domain.

Order matters:

1. Merge the protected Phase 1 stack and WP-SITE-1.
2. Deploy the default GitHub Pages URL and pass smoke tests.
3. Verify `globalsoilintelligence.com` in the `global-soil-intelligence` GitHub organization using
   the GitHub-generated DNS TXT record. Keep this record after verification.
4. Add `globalsoilintelligence.com` as the repository’s Pages custom domain.
5. In Squarespace DNS, preserve all email-related MX, SPF, DKIM, and DMARC records.
6. Remove only conflicting Squarespace web-hosting records.
7. Add the four current GitHub Pages `A` records for the apex:
   - `185.199.108.153`
   - `185.199.109.153`
   - `185.199.110.153`
   - `185.199.111.153`
8. Add `CNAME` `www` → `global-soil-intelligence.github.io`.
9. Do not create wildcard DNS records.
10. Wait for DNS and certificate issuance, then enable **Enforce HTTPS**.
11. Verify apex, `www`, HTTPS, redirects, canonical tags, and every application/download path.
12. Turn the Squarespace domain lock on after DNS work. Keep WHOIS privacy, DNSSEC, and auto-renew
    enabled.

Reconfirm GitHub’s published DNS values immediately before the production edit rather than relying
only on this document.

## 9. Acceptance tests

### Functional

- Every URL in §3 returns the intended page or artifact over HTTPS.
- Header/footer navigation and every CTA resolve without a broken link.
- Existing capture offline/reconnect and map-layer journeys remain green.
- Both reference-card PDFs download and render.
- The data page does not link to a nonexistent dataset.
- Service/data failures show an honest unavailable or not-yet-published state.

### Responsive and browser

- Verify at 320, 390, 768, 1024, and 1440 CSS pixels.
- Desktop Chromium, mobile Chromium, and mobile WebKit automated journeys pass.
- Manual verification on a real iPhone Safari and Android Chrome before announcement.

### Accessibility

- WCAG 2.2 AA target.
- Complete keyboard navigation with a visible focus state.
- Skip link, landmarks, semantic headings, labels, alt text, and polite live regions.
- Automated accessibility scan reports no serious or critical findings.
- Text and controls meet AA contrast in every state.
- At 200% zoom, no content or controls become unavailable.

### Performance

- Homepage Lighthouse targets: Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 95,
  SEO ≥ 95 on the mobile profile.
- Homepage initial compressed transfer ≤ 700 KB, excluding a user-initiated PDF download.
- No MapLibre bundle or full-resolution print PDF loads on the homepage.
- No layout shift from unsized imagery or fonts.

### Privacy and language

- Repository language guard passes.
- Public source and built assets contain no private key, precise sample coordinate, private camera
  metadata, or contributor identifier.
- No copy claims to provide a “soil test.”
- No Phase 2 estimate or model is presented as live.

### Deployment

- CI lint, format, typecheck, unit tests, production builds, and browser journeys pass.
- GitHub organization domain verification is active.
- DNS answers match GitHub Pages.
- `www` redirects to the canonical apex domain.
- HTTPS is enforced with no mixed content.
- Existing email DNS records remain intact.
- A stranger can open the homepage, understand GSIP, download the card, explore the map, and reach
  the capture flow without instruction.

## 10. Release sequence

1. **SITE-1A — foundation:** scaffold `apps/site-web`, shared tokens/components, multi-page build,
   tests, and Pages packaging.
2. **SITE-1B — content:** homepage, card, methods, data, and about pages with reviewed copy.
3. **SITE-1C — quality:** accessibility, performance, SEO, social preview, link and browser tests.
4. **SITE-1D — domain:** GitHub organization verification, Squarespace DNS, HTTPS, and redirects.
5. **SITE-1E — launch:** legal/privacy gate confirmation, real-phone smoke test, dataset status
   verification, and public announcement.

The code may merge before anonymous capture is enabled. If the legal/privacy gate is still pending,
the homepage and map may launch, but contribution CTAs must lead to an explicit “capture opening
soon” state rather than a production write path.

## 11. Done when

WP-SITE-1 is complete when the site is available at `https://globalsoilintelligence.com`, all
acceptance tests pass, the existing map/capture/card artifacts remain functional, the site makes no
unsupported scientific or launch claims, and a first-time visitor can understand the project and
choose a next action in under 30 seconds.

## 12. Operational references

- GitHub Pages custom domain:
  `https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site`
- GitHub Pages domain verification:
  `https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/verifying-your-custom-domain-for-github-pages`
- Squarespace DNS editing:
  `https://support.squarespace.com/hc/en-us/articles/360002101888-Adding-DNS-records-to-your-domain`
- Squarespace domain locks:
  `https://support.squarespace.com/hc/en-us/articles/360034059332-Domain-locks`
