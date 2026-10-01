import { expect, test } from '@playwright/test'

test('map and capture shells are connected', async ({ page }) => {
  await page.goto('/gsip/map/')
  await expect(page.getByRole('heading')).toContainText('living map')
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
  await page.route('https://supabase.test/**', async (route) => {
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
  await page.evaluate(() => navigator.serviceWorker.ready)
  await page.reload()
  await page.waitForFunction(() => Boolean(navigator.serviceWorker.controller))
  await page.evaluate(() => {
    for (const [name, contents] of [
      ['shot-a', 'context-photo'],
      ['shot-b', 'fresh-photo'],
    ]) {
      const transfer = new DataTransfer()
      transfer.items.add(
        new File([contents], `${name}.jpg`, { type: 'image/jpeg' }),
      )
      const input = document.querySelector<HTMLInputElement>(`[name="${name}"]`)
      if (!input) throw new Error(`Missing ${name} input`)
      input.files = transfer.files
      input.dispatchEvent(new Event('change', { bubbles: true }))
    }
  })
  await page.getByLabel('Land cover').selectOption('cropland')
  await page.getByLabel('Surface condition').selectOption('moist')
  await page.getByLabel('Latitude').fill('41.9483')
  await page.getByLabel('Longitude').fill('-93.625')
  await page.getByRole('checkbox').check()
  await context.setOffline(true)
  await page.getByRole('button', { name: /queue observation/i }).click()
  await expect(page.getByText(/saved offline/i)).toBeVisible()
  await expect(page.getByText('1 queued')).toBeVisible()
  if (browserName !== 'webkit') {
    await page.reload()
    await expect(page.getByText('1 queued')).toBeVisible()
  }
  await context.setOffline(false)
  await expect(page.getByText(/1 observation synced/i)).toBeVisible()
  await expect(page.getByText('1 queued')).not.toBeVisible()
  expect(requestOrder).toEqual(
    expect.arrayContaining([
      'POST /auth/v1/signup',
      'POST /rest/v1/contribution_grants',
      'POST /rest/v1/submissions',
    ]),
  )
})
