import { expect, test, type BrowserContext, type Page } from '@playwright/test'

/**
 * WP-COLLECT-4B2: the optional framing guide in a real browser. The camera is a synthetic canvas
 * stream with a different colour in each corner, the account and service are mocked on a
 * reserved `.test` host, and nothing here uses a sensor, a real record or a deployed artifact.
 */

const owner = '30000000-0000-4000-8000-000000000099'
const contributor = '20000000-0000-4000-8000-000000000099'
const WIDTH = 1280
const HEIGHT = 960

function token() {
  const encode = (value: unknown) =>
    Buffer.from(JSON.stringify(value)).toString('base64url')
  return `${encode({ alg: 'HS256', typ: 'JWT' })}.${encode({ aud: 'authenticated', sub: owner, role: 'authenticated', exp: Math.floor(Date.now() / 1000) + 3600 })}.synthetic-signature`
}

/** Replaces the camera with a canvas stream and records every media call the page makes. */
async function syntheticCamera(context: BrowserContext) {
  await context.addInitScript(
    ({ width, height }) => {
      const state = {
        calls: [] as unknown[],
        enumerations: 0,
        tracks: [] as MediaStreamTrack[],
      }
      Object.assign(window, { __camera: state })
      const devices = navigator.mediaDevices
      if (!devices) return
      // Defined on the prototype: some engines ignore assignment to the instance.
      const replace = (name: string, value: unknown) =>
        Object.defineProperty(MediaDevices.prototype, name, {
          configurable: true,
          writable: true,
          value,
        })
      replace('enumerateDevices', async () => {
        state.enumerations += 1
        return []
      })
      replace('getUserMedia', async (constraints: MediaStreamConstraints) => {
        state.calls.push(constraints)
        const canvas = document.createElement('canvas')
        canvas.width = width
        canvas.height = height
        const context = canvas.getContext('2d')!
        const paint = () => {
          context.fillStyle = '#806040'
          context.fillRect(0, 0, width, height)
          const corner = 240
          for (const [x, y, colour] of [
            [0, 0, '#ff0000'],
            [width - corner, 0, '#00ff00'],
            [0, height - corner, '#0000ff'],
            [width - corner, height - corner, '#ffff00'],
          ] as const) {
            context.fillStyle = colour
            context.fillRect(x, y, corner, corner)
          }
        }
        paint()
        const timer = window.setInterval(paint, 40)
        const stream = canvas.captureStream(25)
        for (const track of stream.getTracks()) {
          state.tracks.push(track)
          track.addEventListener('ended', () => window.clearInterval(timer))
        }
        return stream
      })
    },
    { width: WIDTH, height: HEIGHT },
  )
}

type Service = {
  admitted: boolean
  uploads: Array<{ path: string; body: Buffer | null }>
  unexpected: string[]
}

async function syntheticService(context: BrowserContext): Promise<Service> {
  const service: Service = { admitted: true, uploads: [], unexpected: [] }
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
    const request = route.request()
    const url = new URL(request.url())
    const method = request.method()
    if (url.origin === 'http://127.0.0.1:4173') return route.continue()
    if (url.protocol === 'blob:' || url.protocol === 'data:')
      return route.continue()
    if (url.origin !== 'https://supabase.test') {
      service.unexpected.push(url.origin)
      return route.abort()
    }
    const json = (value: unknown, status = 200) =>
      route.fulfill({
        body: JSON.stringify(value),
        contentType: 'application/json',
        status,
      })
    if (url.pathname === '/auth/v1/user' && method === 'GET') return json(user)
    if (url.pathname === '/rest/v1/rpc/collection_pilot_capabilities')
      return json({
        version: 'gsip-invited-pilot-v1',
        mode: 'invited_private',
        member: service.admitted,
        capture_open: service.admitted,
        library_intake_available: service.admitted,
        publication_held: true,
      })
    if (url.pathname === '/rest/v1/rpc/library_intake_capabilities')
      return json({
        version: 'gsip-library-intake-v1',
        available: service.admitted,
      })
    if (url.pathname === '/rest/v1/service_state')
      return json([{ capture_open: service.admitted }])
    if (url.pathname === '/rest/v1/contributors' && method === 'GET')
      return json([{ id: contributor }])
    if (url.pathname === '/rest/v1/rpc/finalize_submission') return json({})
    if (url.pathname.startsWith('/storage/v1/object/incoming-photos/')) {
      service.uploads.push({
        path: url.pathname,
        body: request.postDataBuffer(),
      })
      return json({ Key: url.pathname })
    }
    if (url.pathname.startsWith('/rest/v1/') && method === 'GET')
      return json([])
    if (url.pathname.startsWith('/rest/v1/') && method === 'POST')
      return route.fulfill({ status: 201, body: '' })
    if (url.pathname === '/functions/v1/prior-attach') return json({})
    service.unexpected.push(`${method} ${url.pathname}`)
    return route.abort()
  })
  return service
}

const camera = (page: Page) =>
  page.evaluate(() => {
    const state = (
      window as unknown as {
        __camera: {
          calls: MediaStreamConstraints[]
          enumerations: number
          tracks: MediaStreamTrack[]
        }
      }
    ).__camera
    return {
      calls: state.calls,
      enumerations: state.enumerations,
      live: state.tracks.filter((track) => track.readyState === 'live').length,
      tracks: state.tracks.length,
    }
  })

/** Decodes JPEG bytes in the page and reads the pixels that matter. */
async function decoded(page: Page, bytes: number[]) {
  return page.evaluate(async (data) => {
    const bitmap = await createImageBitmap(
      new Blob([new Uint8Array(data)], { type: 'image/jpeg' }),
    )
    const canvas = document.createElement('canvas')
    canvas.width = bitmap.width
    canvas.height = bitmap.height
    const context = canvas.getContext('2d')!
    context.drawImage(bitmap, 0, 0)
    const at = (x: number, y: number) =>
      Array.from(context.getImageData(x, y, 1, 1).data.slice(0, 3))
    const w = bitmap.width
    const h = bitmap.height
    // Every pixel outside the four corner squares must be the plain fill. An outline drawn
    // into the frame at any scale or position would put light pixels somewhere in this area.
    const pixels = context.getImageData(0, 0, w, h).data
    const corner = 240 + 24
    let foreign = 0
    for (let y = 0; y < h; y += 1)
      for (let x = 0; x < w; x += 1) {
        if ((x < corner || x >= w - corner) && (y < corner || y >= h - corner))
          continue
        const offset = (y * w + x) * 4
        if (
          Math.abs(pixels[offset]! - 128) > 40 ||
          Math.abs(pixels[offset + 1]! - 96) > 40 ||
          Math.abs(pixels[offset + 2]! - 64) > 40
        )
          foreign += 1
      }
    return {
      width: w,
      height: h,
      topLeft: at(60, 60),
      topRight: at(w - 60, 60),
      bottomLeft: at(60, h - 60),
      bottomRight: at(w - 60, h - 60),
      centre: at(Math.round(w / 2), Math.round(h / 2)),
      foreign,
    }
  }, bytes)
}

const near = (pixel: number[], target: number[]) =>
  pixel.every((value, index) => Math.abs(value - target[index]!) <= 40)

async function signIn(page: Page) {
  await page.goto(
    `/gsip/pilot/#access_token=${token()}&refresh_token=synthetic-refresh&expires_in=3600&token_type=bearer&type=magiclink`,
  )
  await expect(
    page.getByRole('button', { name: /queue observation/i }),
  ).toBeVisible()
}

async function enterGuide(page: Page) {
  const entry = page.getByRole('button', {
    name: 'Use the optional framing guide',
  })
  await expect(entry).toBeEnabled()
  await entry.click()
  await expect(
    page.getByRole('button', { name: 'Take photo A with the guide' }),
  ).toBeVisible()
}

async function takeWithGuide(page: Page, shot: 'A' | 'B') {
  await page
    .getByRole('button', { name: `Take photo ${shot} with the guide` })
    .click()
  const dialog = page.getByRole('dialog', {
    name: `Framing guide: photo ${shot}`,
  })
  await dialog.getByRole('button', { name: 'Start camera' }).click()
  const shutter = dialog.getByRole('button', {
    name: `Take photo ${shot}`,
    exact: true,
  })
  await expect(shutter).toBeEnabled()
  return { dialog, shutter }
}

test('guide photos keep the whole frame, its orientation and no outline, and queue privately', async ({
  page,
  context,
}) => {
  await syntheticCamera(context)
  const service = await syntheticService(context)
  await signIn(page)
  expect((await camera(page)).calls).toHaveLength(0)

  await enterGuide(page)
  await expect(page.locator('.photo-grid input[type=file]')).toHaveCount(0)
  expect((await camera(page)).calls).toHaveLength(0)

  const first = await takeWithGuide(page, 'A')
  const state = await camera(page)
  expect(state.calls).toHaveLength(1)
  expect(state.calls[0]!.audio).toBe(false)
  expect(state.enumerations).toBe(0)
  expect(state.live).toBe(1)

  // The outline is on screen, inside the picture the video shows.
  const outline = first.dialog.getByTestId('guide-outline')
  await expect(outline).toBeVisible()
  const outlineBox = (await outline.boundingBox())!
  const stageBox = (await first.dialog
    .getByTestId('guide-stage')
    .boundingBox())!
  expect(outlineBox.width / outlineBox.height).toBeCloseTo(WIDTH / HEIGHT, 1)
  expect(outlineBox.x).toBeGreaterThanOrEqual(stageBox.x - 1)
  expect(outlineBox.y).toBeGreaterThanOrEqual(stageBox.y - 1)
  const video = first.dialog.locator('video')
  expect(
    await video.evaluate((element) => getComputedStyle(element).transform),
  ).toBe('none')

  await first.shutter.click()
  const review = first.dialog.getByAltText(
    'Photo A as taken, before you choose it',
  )
  await expect(review).toBeVisible()
  expect((await camera(page)).live).toBe(0)
  await expect(first.dialog.getByTestId('guide-outline')).toHaveCount(0)
  await first.dialog.getByRole('button', { name: 'Use photo' }).click()
  await expect(first.dialog).toHaveCount(0)

  const second = await takeWithGuide(page, 'B')
  await second.shutter.click()
  await second.dialog.getByRole('button', { name: 'Use photo' }).click()
  await expect(second.dialog).toHaveCount(0)
  expect((await camera(page)).calls).toHaveLength(2)
  expect((await camera(page)).live).toBe(0)
  expect(service.uploads).toHaveLength(0)

  await page.getByLabel('Land cover').selectOption('cropland')
  await page.getByLabel('Surface condition').selectOption('moist')
  await page.getByLabel('Latitude', { exact: true }).fill('1')
  await page.getByLabel('Longitude', { exact: true }).fill('1')
  await page.getByRole('checkbox', { name: /sampling rules/i }).check()
  await page.getByRole('checkbox', { name: /I am at least 18/i }).check()
  await page.getByRole('button', { name: /queue observation/i }).click()
  await expect.poll(() => service.uploads.length).toBe(2)
  expect(
    service.uploads.every((upload) => upload.path.includes(`/${owner}/`)),
  ).toBe(true)

  // What left the page is the full synthetic frame: right way up, unmirrored, with no outline.
  for (const upload of service.uploads) {
    const bytes = Array.from(upload.body!)
    expect(bytes.slice(0, 3)).toEqual([0xff, 0xd8, 0xff])
    const image = await decoded(page, bytes)
    expect([image.width, image.height]).toEqual([WIDTH, HEIGHT])
    expect(near(image.topLeft, [255, 0, 0])).toBe(true)
    expect(near(image.topRight, [0, 255, 0])).toBe(true)
    expect(near(image.bottomLeft, [0, 0, 255])).toBe(true)
    expect(near(image.bottomRight, [255, 255, 0])).toBe(true)
    expect(near(image.centre, [128, 96, 64])).toBe(true)
    expect(image.foreign).toBe(0)
  }
  await expect(
    page.getByRole('button', { name: 'Use the optional framing guide' }),
  ).toBeVisible()
  expect(service.unexpected).toEqual([])
})

test('Escape, cancel and a hidden page each turn the camera off, and nothing restarts it', async ({
  page,
  context,
}) => {
  await syntheticCamera(context)
  await syntheticService(context)
  await signIn(page)
  await enterGuide(page)

  const first = await takeWithGuide(page, 'A')
  expect((await camera(page)).live).toBe(1)
  await page.keyboard.press('Escape')
  await expect(first.dialog).toHaveCount(0)
  expect((await camera(page)).live).toBe(0)

  // A second Escape with nothing open does nothing, and the guide is still usable.
  await page.keyboard.press('Escape')
  const second = await takeWithGuide(page, 'A')
  await second.dialog.getByRole('button', { name: 'Cancel' }).click()
  await expect(second.dialog).toHaveCount(0)
  expect((await camera(page)).live).toBe(0)

  const third = await takeWithGuide(page, 'A')
  await third.shutter.click()
  await third.dialog.getByRole('button', { name: 'Use photo' }).click()
  await expect(page.getByAltText('Guide photo A, not saved yet')).toBeVisible()
  const fourth = await takeWithGuide(page, 'B')
  expect((await camera(page)).live).toBe(1)
  await page.evaluate(() => {
    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      get: () => 'hidden',
    })
    document.dispatchEvent(new Event('visibilitychange', { bubbles: true }))
  })
  await expect(fourth.dialog).toHaveCount(0)
  expect((await camera(page)).live).toBe(0)
  await expect(page.getByAltText('Guide photo A, not saved yet')).toHaveCount(0)
  const calls = (await camera(page)).calls.length
  await page.evaluate(() => {
    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      get: () => 'visible',
    })
    document.dispatchEvent(new Event('visibilitychange', { bubbles: true }))
    window.dispatchEvent(new Event('focus'))
    window.dispatchEvent(new Event('pageshow'))
  })
  await page.waitForTimeout(500)
  expect((await camera(page)).calls).toHaveLength(calls)
  await page
    .getByRole('button', { name: 'Check access and show guide photos' })
    .click()
  await expect(page.getByAltText('Guide photo A, not saved yet')).toBeVisible()
  expect((await camera(page)).calls).toHaveLength(calls)
})

test('a refused camera falls back to the picker without asking again', async ({
  page,
  context,
}) => {
  await syntheticCamera(context)
  await context.addInitScript(() => {
    const state = (window as unknown as { __camera: { calls: unknown[] } })
      .__camera
    if (!navigator.mediaDevices) return
    Object.defineProperty(MediaDevices.prototype, 'getUserMedia', {
      configurable: true,
      writable: true,
      value: async (constraints: MediaStreamConstraints) => {
        state.calls.push(constraints)
        throw new DOMException('synthetic refusal', 'NotAllowedError')
      },
    })
  })
  await syntheticService(context)
  await signIn(page)
  await enterGuide(page)
  await page
    .getByRole('button', { name: 'Take photo A with the guide' })
    .click()
  const dialog = page.getByRole('dialog')
  await dialog.getByRole('button', { name: 'Start camera' }).click()
  await expect(dialog.getByRole('status')).toContainText('not allowed')
  await expect(
    dialog.getByRole('button', { name: /Start camera/ }),
  ).toHaveCount(0)
  await dialog
    .getByRole('button', { name: 'Use the camera or gallery instead' })
    .click()
  await expect(dialog).toHaveCount(0)
  await expect(page.locator('.photo-grid input[type=file]')).toHaveCount(3)
  expect((await camera(page)).calls).toHaveLength(1)
})

test('the closed capture page and the rights view never offer the guide or touch the camera', async ({
  page,
  context,
}) => {
  await syntheticCamera(context)
  const service = await syntheticService(context)
  service.admitted = false
  for (const path of ['/gsip/closed-capture/', '/gsip/pilot/#your-data']) {
    await page.goto('about:blank')
    await page.goto(path)
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    await page.waitForTimeout(300)
    await expect(
      page.getByRole('button', { name: 'Use the optional framing guide' }),
    ).toHaveCount(0)
    await expect(page.getByRole('dialog')).toHaveCount(0)
    const state = await camera(page)
    expect(state.calls).toHaveLength(0)
    expect(state.enumerations).toBe(0)
  }
})
