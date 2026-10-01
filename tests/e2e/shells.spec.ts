import { expect, test } from '@playwright/test'

test('map and capture shells are connected', async ({ page }) => {
  await page.goto('/gsip/map/')
  await expect(page.getByRole('heading')).toContainText('living map')
  await page.getByRole('link', { name: /contribute/i }).click()
  await expect(page.getByRole('heading')).toContainText('Soil capture')
})
