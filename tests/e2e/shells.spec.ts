import { expect, test } from '@playwright/test'

test('map and capture shells are connected', async ({ page }) => {
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

test('airplane-mode capture remains queued after reload', async ({
  page,
  context,
  browserName,
}) => {
  await page.goto('/gsip/capture/')
  await page.evaluate(() => navigator.serviceWorker.ready)
  await page.reload()
  await page.waitForFunction(() => Boolean(navigator.serviceWorker.controller))
  for (const name of ['shot-a', 'shot-b'])
    await page.locator(`[name="${name}"]`).setInputFiles({
      buffer: Buffer.from(`${name}-fixture`),
      mimeType: 'image/jpeg',
      name: `${name}.jpg`,
    })
  await page.getByLabel('Land cover').selectOption('cropland')
  await page.getByLabel('Surface condition').selectOption('moist')
  await page.getByLabel('Latitude').fill('41.9483')
  await page.getByLabel('Longitude').fill('-93.625')
  await page.getByRole('checkbox').check()
  if (browserName !== 'webkit') await context.setOffline(true)
  await page
    .locator('form')
    .evaluate((form) =>
      form.dispatchEvent(
        new Event('submit', { bubbles: true, cancelable: true }),
      ),
    )
  await expect(page.getByText(/saved offline|sync paused/i)).toBeVisible()
  await expect(page.getByText('1 queued')).toBeVisible()
  // Playwright WebKit currently aborts offline navigations with an internal
  // engine error, so WebKit verifies reload persistence while Chromium also
  // exercises a genuinely disconnected service-worker navigation.
  await page.reload()
  await expect(page.getByText('1 queued')).toBeVisible()
  if (browserName !== 'webkit') await context.setOffline(false)
})
