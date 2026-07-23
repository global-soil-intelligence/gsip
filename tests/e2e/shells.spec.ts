import { readFileSync } from 'node:fs'
import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

const jpegFixture = readFileSync('tests/e2e/fixtures/photo.jpg')

test('public information pages have no serious accessibility violations', async ({
  page,
}) => {
  const failures: Array<{
    impact: string | null
    page: string
    rule: string
    targets: string
  }> = []
  for (const path of ['', 'card/', 'methods/', 'data/', 'about/']) {
    await page.goto(`/gsip/${path}`)
    const result = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
      .analyze()
    failures.push(
      ...result.violations
        .filter(({ impact }) => impact === 'critical' || impact === 'serious')
        .map(({ id, impact, nodes }) => ({
          impact,
          page: path || '/',
          rule: id,
          targets: nodes.flatMap(({ target }) => target).join(', '),
        })),
    )
  }
  expect(failures).toEqual([])
})

test('public hub explains the project and connects its core paths', async ({
  page,
}) => {
  await page.goto('/gsip/')
  await expect(
    page.getByRole('heading', {
      level: 1,
      name: 'Build the world’s living soil map.',
    }),
  ).toBeVisible()
  await expect(
    page.getByRole('link', { name: 'Capture opening soon' }).first(),
  ).toBeVisible()
  await page
    .getByRole('navigation', { name: 'Primary navigation' })
    .getByRole('link', { name: 'Print card' })
    .click()
  await expect(
    page.getByRole('heading', {
      level: 1,
      name: 'Give every phone camera a reference point.',
    }),
  ).toBeVisible()
  await expect(
    page.getByRole('link', { name: 'Download color PDF' }),
  ).toHaveAttribute(
    'href',
    '../reference-card/gsip-reference-card-v1-color.pdf',
  )
  await page
    .getByRole('navigation', { name: 'Primary navigation' })
    .getByRole('link', { name: 'Methods' })
    .click()
  await expect(
    page.getByRole('heading', {
      level: 1,
      name: 'Scientific honesty is part of the architecture.',
    }),
  ).toBeVisible()
})

test('map and capture shells are connected', async ({ page }) => {
  await page.route('https://supabase.test/rest/v1/h3_cells**', (route) =>
    route.fulfill({
      body: JSON.stringify([
        {
          h3_index: '88262b2a37fffff',
          latest_submission_date: '2026-07-23',
          n_submissions: 1,
        },
      ]),
      contentType: 'application/json',
      status: 200,
    }),
  )
  await page.goto('/gsip/map/')
  await expect(page.getByRole('heading')).toContainText('Read the ground')
  await expect(page.getByText(/public H3 cells loaded/i)).toBeVisible()
  await page.getByRole('button', { name: /Soil pH/i }).click()
  await expect(page.getByRole('button', { name: /Soil pH/i })).toHaveAttribute(
    'aria-pressed',
    'true',
  )
  await page.getByRole('link', { name: /contribute/i }).click()
  await expect(page.getByRole('heading', { level: 1 })).toContainText(
    'Help map',
  )
})

test('airplane-mode capture persists then syncs through the hosted path', async ({
  page,
  context,
  browserName,
}) => {
  const requestOrder: string[] = []
  await context.route('https://supabase.test/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const method = request.method()
    requestOrder.push(`${method} ${url.pathname}`)
    const json = (body: unknown, status = 200) =>
      route.fulfill({
        body: JSON.stringify(body),
        contentType: 'application/json',
        status,
      })

    if (url.pathname === '/auth/v1/signup') {
      const timestamp = '2026-07-23T00:00:00Z'
      return json({
        access_token: 'e2e-access-token',
        expires_in: 3600,
        refresh_token: 'e2e-refresh-token',
        token_type: 'bearer',
        user: {
          app_metadata: { provider: 'anonymous', providers: ['anonymous'] },
          aud: 'authenticated',
          created_at: timestamp,
          id: '30000000-0000-4000-8000-000000000099',
          identities: [],
          is_anonymous: true,
          role: 'authenticated',
          updated_at: timestamp,
          user_metadata: {},
        },
      })
    }
    if (url.pathname === '/rest/v1/contributors' && method === 'GET')
      return json([])
    if (url.pathname === '/rest/v1/contributors' && method === 'POST') {
      return json({ id: '20000000-0000-4000-8000-000000000099' }, 201)
    }
    if (url.pathname.startsWith('/rest/v1/') && method === 'GET')
      return json([])
    if (url.pathname.startsWith('/rest/v1/') && method === 'POST') {
      return route.fulfill({ body: '', status: 201 })
    }
    if (url.pathname.startsWith('/storage/v1/object/incoming-photos/')) {
      return json({ Key: url.pathname }, 200)
    }
    if (url.pathname === '/functions/v1/prior-attach') return json({})
    return route.abort('failed')
  })
  await page.goto('/gsip/capture/')
  if (browserName !== 'webkit') {
    await page.evaluate(() => navigator.serviceWorker.ready)
    await page.reload()
    await page.waitForFunction(() =>
      Boolean(navigator.serviceWorker.controller),
    )
  }
  for (const name of ['shot-a', 'shot-b']) {
    await page.locator(`[name="${name}"]`).setInputFiles({
      buffer: jpegFixture,
      mimeType: 'image/jpeg',
      name: `${name}.jpg`,
    })
    // Keep a browser-memory copy. Playwright WebKit's temporary upload file
    // becomes unreadable when its network context enters offline mode.
    await page.locator(`[name="${name}"]`).evaluate(async (input) => {
      const source = (input as HTMLInputElement).files?.[0]
      if (!source) throw new Error('JPEG fixture was not attached')
      const transfer = new DataTransfer()
      transfer.items.add(
        new File([await source.arrayBuffer()], source.name, {
          lastModified: source.lastModified,
          type: source.type,
        }),
      )
      ;(input as HTMLInputElement).files = transfer.files
    })
  }
  await page.getByLabel('Land cover').selectOption('cropland')
  await page.getByLabel('Surface condition').selectOption('moist')
  await page.getByLabel('Latitude').fill('41.9483')
  await page.getByLabel('Longitude').fill('-93.625')
  await page.getByRole('checkbox').check()
  if (browserName === 'webkit') {
    // WebKit's Playwright transport cannot read a temporary camera file after
    // context.setOffline(true). Its browser project blocks service workers so
    // cross-origin hosted-path mocks remain observable.
    await page.evaluate(() => {
      Object.defineProperty(navigator, 'onLine', {
        configurable: true,
        value: false,
      })
    })
  } else {
    await context.setOffline(true)
  }
  await page.getByRole('button', { name: /queue observation/i }).click()
  await expect(page.getByText(/saved offline/i)).toBeVisible()
  await expect(page.getByText('1 queued')).toBeVisible()
  if (browserName !== 'webkit') {
    await page.reload()
    await expect(page.getByText('1 queued')).toBeVisible()
    await context.setOffline(false)
  } else {
    await page.evaluate(() => {
      Object.defineProperty(navigator, 'onLine', {
        configurable: true,
        value: true,
      })
      window.dispatchEvent(new Event('online'))
    })
  }
  await expect
    .poll(() => requestOrder)
    .toEqual(
      expect.arrayContaining([
        'POST /auth/v1/signup',
        'POST /rest/v1/contribution_grants',
        'POST /rest/v1/submissions',
      ]),
    )
  await expect(page.getByText(/1 observation synced/i)).toBeVisible()
  await expect(page.getByText('1 queued')).not.toBeVisible()
})
