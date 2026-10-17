import { readFileSync } from 'node:fs'
import { expect, test } from '@playwright/test'

const photo = readFileSync('tests/e2e/fixtures/photo.jpg')
const owner = '30000000-0000-4000-8000-000000000099'
const contributor = '20000000-0000-4000-8000-000000000099'
function token() {
  const encode = (value: unknown) =>
    Buffer.from(JSON.stringify(value)).toString('base64url')
  return `${encode({ alg: 'HS256', typ: 'JWT' })}.${encode({ aud: 'authenticated', sub: owner, role: 'authenticated', exp: Math.floor(Date.now() / 1000) + 3600 })}.synthetic-signature`
}

for (const rights of ['withdrawal', 'account deletion'] as const) {
  test(`invited browser retries private intake and retains ${rights} through closed rollback recovery`, async ({
    page,
    context,
  }) => {
    const requests: Array<{
      method: string
      path: string
      body: Record<string, unknown> | null
    }> = []
    const unexpected: string[] = []
    const intakes: unknown[] = []
    let admitted = true
    let loseReceipt = true
    const user = {
      id: owner,
      aud: 'authenticated',
      role: 'authenticated',
      is_anonymous: false,
      email: 'invited@example.test',
      app_metadata: { provider: 'email', providers: ['email'] },
      user_metadata: {},
      identities: [],
      created_at: '2026-10-16T00:00:00Z',
    }
    await context.route('**/*', async (route) => {
      const request = route.request(),
        url = new URL(request.url()),
        method = request.method()
      if (url.origin === 'http://127.0.0.1:4173') return route.continue()
      if (url.origin !== 'https://supabase.test') {
        unexpected.push(url.origin)
        return route.abort()
      }
      let body: Record<string, unknown> | null = null
      if (
        request.postData() &&
        request.headers()['content-type']?.includes('application/json')
      )
        body = request.postDataJSON()
      requests.push({ method, path: url.pathname, body })
      const json = (value: unknown, status = 200) =>
        route.fulfill({
          body: JSON.stringify(value),
          contentType: 'application/json',
          status,
        })
      if (url.pathname === '/auth/v1/otp' && method === 'POST') return json({})
      if (url.pathname === '/auth/v1/user' && method === 'GET')
        return json(user)
      if (url.pathname === '/auth/v1/logout' && method === 'POST')
        return route.fulfill({ status: 204, body: '' })
      if (url.pathname === '/rest/v1/rpc/collection_pilot_capabilities')
        return json({
          version: 'gsip-invited-pilot-v1',
          mode: 'invited_private',
          member: admitted,
          capture_open: admitted,
          library_intake_available: admitted,
          publication_held: true,
        })
      if (url.pathname === '/rest/v1/rpc/library_intake_capabilities')
        return json({ version: 'gsip-library-intake-v1', available: admitted })
      if (url.pathname === '/rest/v1/service_state')
        return json([{ capture_open: admitted }])
      if (url.pathname === '/rest/v1/contributors' && method === 'GET')
        return json([{ id: contributor }])
      if (url.pathname === '/rest/v1/rpc/finalize_submission') return json({})
      if (url.pathname === '/rest/v1/rpc/record_library_intake') {
        intakes.push(body?.p_request)
        if (loseReceipt) {
          loseReceipt = false
          return json({ message: 'Synthetic lost receipt' }, 503)
        }
        return json({
          intake_id: (body?.p_request as { intake_id: string }).intake_id,
          status: 'already_stored',
        })
      }
      if (url.pathname.startsWith('/storage/v1/object/incoming-photos/'))
        return json({ Key: url.pathname })
      if (url.pathname.startsWith('/rest/v1/') && method === 'GET')
        return json([])
      if (url.pathname.startsWith('/rest/v1/') && method === 'POST')
        return route.fulfill({ status: 201, body: '' })
      if (url.pathname === '/functions/v1/prior-attach') return json({})
      unexpected.push(`${method} ${url.pathname}`)
      return route.abort()
    })
    await page.clock.install()
    await page.goto('/gsip/pilot/')
    await expect(
      page.getByText('No printed card needed.', { exact: true }),
    ).toBeVisible()
    await expect(
      page.getByRole('link', { name: /optional printable A6 card/i }),
    ).toHaveAttribute(
      'href',
      /reference-card\/gsip-reference-card-v1-color\.pdf$/,
    )
    const cardHelp = page.getByText('Optional physical reference card', {
      exact: true,
    })
    await cardHelp.click()
    await expect(
      page.getByText(/not a certified reflectance target/),
    ).toBeVisible()

    await expect(
      page.getByRole('button', { name: /queue observation/i }),
    ).toHaveCount(0)
    await expect(page.locator('input[type=file]')).toHaveCount(0)
    await page.getByLabel('Email').fill('invited@example.test')
    await page.getByRole('button', { name: 'Send magic link' }).click()
    await expect
      .poll(
        () =>
          requests.find((r) => r.path === '/auth/v1/otp')?.body?.create_user,
      )
      .toBe(false)
    // Simulate the delivered callback using the real SDK; no auth/session code is injected.
    await page.goto('about:blank')
    await page.goto(
      `/gsip/pilot/#access_token=${token()}&refresh_token=synthetic-refresh&expires_in=3600&token_type=bearer&type=magiclink`,
    )
    await expect(
      page.getByRole('button', { name: /queue observation/i }),
    ).toBeVisible()
    for (const shot of ['A', 'B'])
      await page.getByLabel(new RegExp(`${shot} ·`)).setInputFiles({
        buffer: photo,
        mimeType: 'image/jpeg',
        name: `synthetic-${shot}.jpg`,
      })
    await page.getByLabel('Land cover').selectOption('cropland')
    await page.getByLabel('Surface condition').selectOption('moist')
    await page.getByLabel('Latitude', { exact: true }).fill('1')
    await page.getByLabel('Longitude', { exact: true }).fill('1')
    await page
      .getByRole('checkbox', { name: /add a private library sample/i })
      .click()
    await expect(
      page.getByRole('checkbox', { name: /add a private library sample/i }),
    ).toBeChecked()
    await expect(page.getByLabel('Depth top (cm)')).toHaveValue('')
    await expect(page.getByLabel('Depth bottom (cm)')).toHaveValue('')
    const advanced = page.getByText(
      'Advanced: instrument declaration (optional)',
      { exact: true },
    )
    await expect(advanced).toBeVisible()
    await expect(page.getByLabel(/Instrument declaration JSON/)).toBeHidden()
    await advanced.click()
    await expect(page.getByLabel(/Instrument declaration JSON/)).toBeVisible()
    await advanced.click()
    await expect(page.getByLabel(/Instrument declaration JSON/)).toBeHidden()
    await page.getByLabel('Depth top (cm)').fill('0')
    await page.getByLabel('Depth bottom (cm)').fill('5')
    await expect(
      page.getByRole('checkbox', { name: /I am at least 18/i }),
    ).not.toBeChecked()
    await page.getByRole('checkbox', { name: /sampling rules/i }).check()
    await page.getByRole('checkbox', { name: /I am at least 18/i }).check()
    await page.getByRole('button', { name: /queue observation/i }).click()
    await expect.poll(() => intakes.length).toBe(1)
    await expect(page.getByText('1 queued')).toBeVisible()
    const uploads = requests
      .filter((r) => r.path.startsWith('/storage/v1/object/incoming-photos/'))
      .map((r) => r.path)
    expect(uploads).toHaveLength(2)
    expect(uploads.every((path) => path.includes(`/${owner}/`))).toBe(true)
    await page.clock.runFor(30_001)
    await expect.poll(() => intakes.length).toBe(2)
    expect(intakes[1]).toEqual(intakes[0])
    expect(
      requests
        .filter((r) => r.path.startsWith('/storage/v1/object/incoming-photos/'))
        .map((r) => r.path),
    ).toEqual(uploads)
    await expect(page.getByText(/1 observation synced/i)).toBeVisible()
    const accepted = requests.find(
      (r) => r.path === '/rest/v1/contribution_grants' && r.method === 'POST',
    )?.body
    expect(accepted?.terms_version).toBe('2026-07-22-v1')
    expect(typeof accepted?.accepted_at).toBe('string')
    const intakeWrites = requests.filter(
      (r) => r.method === 'POST' && r.path !== '/auth/v1/otp',
    ).length
    admitted = false
    // End the pilot document before measuring a fresh closed landing's network activity.
    await page.goto('about:blank')
    const activation = await page.request.get(
      '/gsip/closed-capture/gsip-activation.json',
    )
    expect(await activation.json()).toEqual({
      capture_live: false,
      library_intake_live: false,
    })
    const beforeClosed = requests.length
    const beforeCapabilities = requests.filter(
      (r) => r.path === '/rest/v1/rpc/collection_pilot_capabilities',
    ).length
    await page.goto('/gsip/closed-capture/')
    await expect(
      page.getByRole('heading', { name: 'Collection is not open yet.' }),
    ).toBeVisible()
    await expect(page.getByLabel('Email')).toHaveCount(0)
    await page.clock.runFor(30_001)
    expect(requests).toHaveLength(beforeClosed)
    await page.goto('/gsip/closed-capture/?view=your-data#your-data')
    await expect(
      page.getByRole('heading', { name: 'Your data and account' }),
    ).toBeVisible()
    await expect(page.locator('input[type=file]')).toHaveCount(0)
    await expect(
      page.getByRole('button', { name: /queue observation/i }),
    ).toHaveCount(0)
    await page.getByLabel('Email').fill('invited@example.test')
    await page.getByRole('button', { name: 'Send magic link' }).click()
    await expect
      .poll(() => requests.filter((r) => r.path === '/auth/v1/otp').length)
      .toBe(2)
    const beforeRecovery = requests.filter(
      (r) => r.path === '/auth/v1/user',
    ).length
    await page.goto('about:blank')
    await page.goto(
      `/gsip/closed-capture/?view=your-data#access_token=${token()}&refresh_token=synthetic-refresh&expires_in=3600&token_type=bearer&type=magiclink`,
    )
    await expect
      .poll(() => requests.filter((r) => r.path === '/auth/v1/user').length)
      .toBeGreaterThan(beforeRecovery)
    await expect(page.locator('input[type=file]')).toHaveCount(0)
    expect(
      requests.filter(
        (r) => r.path === '/rest/v1/rpc/collection_pilot_capabilities',
      ),
    ).toHaveLength(beforeCapabilities)
    await page
      .getByRole('button', {
        name:
          rights === 'withdrawal'
            ? /withdraw my contributions/i
            : /delete my account/i,
      })
      .click()
    await page
      .getByLabel(/to confirm/i)
      .fill(rights === 'withdrawal' ? 'WITHDRAW' : 'DELETE')
    await page
      .getByRole('button', { name: new RegExp(`confirm ${rights}`, 'i') })
      .click()
    await expect
      .poll(
        () =>
          requests.filter(
            (r) =>
              r.method === 'POST' && r.path === '/rest/v1/deletion_requests',
          ).length,
      )
      .toBe(1)
    expect(
      requests.filter(
        (r) =>
          r.method === 'POST' &&
          ![
            '/auth/v1/otp',
            '/auth/v1/logout',
            '/rest/v1/deletion_requests',
            '/rest/v1/grant_withdrawals',
          ].includes(r.path),
      ),
    ).toHaveLength(intakeWrites)
    expect(
      requests.some(
        (r) =>
          r.path === '/auth/v1/signup' ||
          (r.path === '/auth/v1/user' && r.method !== 'GET'),
      ),
    ).toBe(false)
    expect(
      requests
        .filter((r) => r.path === '/auth/v1/otp')
        .every((r) => r.body?.create_user === false),
    ).toBe(true)
    if (rights === 'account deletion')
      await expect
        .poll(() => requests.filter((r) => r.path === '/auth/v1/logout').length)
        .toBe(1)
    expect(unexpected).toEqual([])
  })
}
