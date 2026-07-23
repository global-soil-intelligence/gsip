import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test('mobile navigation, draft recovery, and readable layouts', async ({
  page,
}) => {
  await page.route('https://supabase.test/**', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
  )
  await page.goto('/gsip/capture/')
  await expect(page.getByRole('heading', { level: 1 })).toContainText(
    'A living atlas',
  )
  for (const name of ['Learn', 'Account', 'My observations', 'Capture']) {
    await page.getByRole('button', { name, exact: true }).click()
    await expect(
      page.getByRole('button', { name, exact: true }),
    ).toHaveAttribute('aria-current', 'page')
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true)
  }
  await page.getByLabel('Land cover').selectOption('forest')
  await page.getByLabel('Latitude', { exact: true }).fill('40.4')
  await page.getByLabel('Longitude', { exact: true }).fill('-79.9')
  await page.getByRole('button', { name: 'Save draft on this device' }).click()
  await expect(
    page.getByRole('status').filter({ hasText: 'Draft saved' }),
  ).toBeVisible()
  await page.reload()
  await page.getByRole('button', { name: 'My observations' }).click()
  await page.getByRole('button', { name: 'Resume draft' }).click()
  await expect(page.getByLabel('Latitude', { exact: true })).toHaveValue('40.4')
  await expect(page.getByLabel('Land cover')).toHaveValue('forest')
  await expect(page.getByRole('checkbox')).not.toBeChecked()
  await page.getByRole('button', { name: 'Queue observation securely' }).click()
  await expect(page.getByRole('alert')).toContainText('both required photos')
})

test('mobile screens have no serious accessibility violations', async ({
  page,
}) => {
  await page.goto('/gsip/capture/')
  for (const name of ['Capture', 'My observations', 'Learn', 'Account']) {
    await page.getByRole('button', { name, exact: true }).click()
    const audit = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze()
    expect(
      audit.violations
        .filter((v) => v.impact === 'serious' || v.impact === 'critical')
        .map((v) => ({ id: v.id, targets: v.nodes.map((n) => n.target) })),
    ).toEqual([])
  }
})
