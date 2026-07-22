import { expect, test } from '@playwright/test'

test('map and capture shells are connected', async ({ page }) => {
  await page.goto('/gsip/map/')
  await expect(page.getByRole('heading')).toContainText('living map')
  await page.getByRole('link', { name: /contribute/i }).click()
  await expect(page.getByRole('heading', { level: 1 })).toContainText(
    'Help map',
  )
})

test('airplane-mode capture remains queued after reload', async ({
  page,
  context,
  browserName,
}) => {
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
  await page.getByRole('button', { name: /queue observation/i }).click()
  await expect(page.getByText(/saved offline/i)).toBeVisible()
  await expect(page.getByText('1 queued')).toBeVisible()
  // Playwright WebKit currently aborts offline navigations with an internal
  // engine error, so WebKit verifies reload persistence while Chromium also
  // exercises a genuinely disconnected service-worker navigation.
  if (browserName !== 'webkit') await context.setOffline(true)
  await page.reload()
  await expect(page.getByText('1 queued')).toBeVisible()
  if (browserName !== 'webkit') await context.setOffline(false)
})
