import { readFileSync } from 'node:fs'
import { expect, test, type Worker } from '@playwright/test'

// Fictional, already public-shaped aggregates: no contributor points or private records.
const cells = [
  {
    h3_index: '88262b2a37fffff',
    latest_submission_date: '2026-07-23',
    n_contributors: 3,
    n_submissions: 4,
    resolution: 8,
  },
  {
    h3_index: '86262b2a7ffffff',
    latest_submission_date: '2026-07-20',
    n_contributors: 3,
    n_submissions: 3,
    resolution: 6,
  },
]
const mapLibreLicense = readFileSync(
  `${process.cwd()}/apps/map-web/node_modules/maplibre-gl/LICENSE.txt`,
  'utf8',
).trim()
const transparentPixel = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAACklEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg==',
  'base64',
)

type WorkerGeoJSONSource = {
  _pendingRequest?: unknown
  _geoJSONIndex?: {
    tileIndex?: {
      tiles: Record<
        string,
        {
          source?: Array<{
            tags: {
              h3: string
              contributors: number
              count: number
              resolution: number
              latest: string
            }
          }>
        }
      >
    }
  }
}

for (const path of ['/gsip/map/', '/map/']) {
  test(`built map processes public cells in a real worker at ${path}`, async ({
    page,
    context,
    request,
  }) => {
    const workers: Worker[] = []
    const errors: string[] = []
    const unexpectedOrigins: string[] = []
    const failedLocalResources: string[] = []
    page.on('worker', (worker) => workers.push(worker))
    page.on('pageerror', (error) => errors.push(error.message))
    page.on('console', (message) => {
      if (message.type() === 'error') errors.push(message.text())
    })
    page.on('requestfailed', (failed) => {
      if (new URL(failed.url()).origin === 'http://127.0.0.1:4173')
        failedLocalResources.push(new URL(failed.url()).pathname)
    })
    await context.route('**/*', async (route) => {
      const url = new URL(route.request().url())
      if (url.origin === 'http://127.0.0.1:4173') {
        await route.continue()
      } else if (
        url.origin === 'https://supabase.test' &&
        url.pathname === '/rest/v1/h3_cells'
      ) {
        await route.fulfill({
          body: JSON.stringify(cells),
          contentType: 'application/json',
          status: 200,
        })
      } else if (
        url.origin === 'https://maps.isric.org' &&
        url.pathname.startsWith('/mapserv/')
      ) {
        // The real raster service and legend are irrelevant to worker packaging.
        await route.fulfill({
          body: transparentPixel,
          contentType: 'image/png',
          status: 200,
        })
      } else {
        unexpectedOrigins.push(url.origin)
        await route.abort()
      }
    })

    await page.goto(path)
    await expect(page.getByRole('heading', { level: 1 })).toContainText(
      'Read the ground',
    )
    await expect(
      page.getByText('2 public H3 cells loaded.', { exact: false }),
    ).toBeVisible()
    await expect.poll(() => workers.length).toBeGreaterThan(0)

    for (const worker of workers) {
      const url = new URL(worker.url())
      expect(url.origin).toBe('http://127.0.0.1:4173')
      expect(url.pathname).toMatch(new RegExp(`^${path}assets/.+\\.m?js$`))
      const response = await request.get(worker.url())
      expect(response.status(), 'The built worker must exist').toBe(200)
      expect(response.headers()['content-type']).toMatch(/javascript/)
      expect(await response.text()).not.toMatch(/<!doctype\s+html|<html[\s>]/i)
    }

    const notice = await request.get(`${path}THIRD_PARTY_LICENSES.md`)
    expect(notice.status()).toBe(200)
    expect(await notice.text()).toContain(mapLibreLicense)

    // Inspect the actual library instance in its worker, without replacing messages,
    // processing functions or application state. The locked MapLibre version owns
    // these internals; an empty index or an unfinished request cannot satisfy this.
    // Compare distinct cell tags because tiling may duplicate features for world copies.
    await expect
      .poll(async () => {
        const processed = await Promise.all(
          workers.map((worker) =>
            worker.evaluate((expected) => {
              const scope = globalThis as typeof globalThis & {
                worker?: {
                  workerSources: Record<
                    string,
                    { geojson?: Record<string, WorkerGeoJSONSource> }
                  >
                }
              }
              return Object.values(scope.worker?.workerSources ?? {}).map(
                (sources) => {
                  const source = sources.geojson?.contributions
                  const parsed = Object.values(
                    source?._geoJSONIndex?.tileIndex?.tiles ?? {},
                  ).flatMap((tile) => tile.source ?? [])
                  return {
                    sourceExists: source !== undefined,
                    pendingRequest: source?._pendingRequest !== undefined,
                    indexExists: source?._geoJSONIndex !== undefined,
                    distinctCells: new Set(
                      parsed.map((feature) => feature.tags.h3),
                    ).size,
                    fixtureMatches:
                      parsed.length > 0 &&
                      parsed.every(({ tags }) =>
                        expected.some(
                          (cell) =>
                            tags.h3 === cell.h3_index &&
                            tags.contributors === cell.n_contributors &&
                            tags.count === cell.n_submissions &&
                            tags.resolution === cell.resolution &&
                            tags.latest === cell.latest_submission_date,
                        ),
                      ),
                  }
                },
              )
            }, cells),
          ),
        )
        return processed.flat()
      })
      .toContainEqual({
        sourceExists: true,
        pendingRequest: false,
        indexExists: true,
        distinctCells: 2,
        fixtureMatches: true,
      })
    expect(errors).toEqual([])
    expect(failedLocalResources).toEqual([])
    expect(unexpectedOrigins).toEqual([])
  })
}
