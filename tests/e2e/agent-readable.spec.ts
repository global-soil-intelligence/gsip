import { expect, test } from '@playwright/test'

// WP-AGENT-1: crawlers and agents that do not run JavaScript read the same pages people do.
const PAGES: Array<[path: string, headline: string]> = [
  ['', 'Build the world’s living soil map.'],
  ['card/', 'Give every phone camera a reference point.'],
  ['methods/', 'Scientific honesty is part of the architecture.'],
  ['data/', 'A dataset designed to be used—and scrutinized.'],
  ['about/', 'A shared map for the ground we depend on.'],
]

test.describe('without JavaScript', () => {
  test.use({ javaScriptEnabled: false })

  for (const [path, headline] of PAGES) {
    test(`/${path} shows its headline and structured data`, async ({
      page,
    }) => {
      await page.goto(`/gsip/${path}`)
      await expect(
        page.getByRole('heading', { level: 1, name: headline }),
      ).toBeVisible()
      const graph = JSON.parse(
        (await page
          .locator('script[type="application/ld+json"]')
          .textContent()) ?? '{}',
      )['@graph'] as Array<{ '@type': string }>
      const types = graph.map((node) => node['@type'])
      expect(types).toContain('Organization')
      expect(types.includes('Dataset')).toBe(path === '' || path === 'data/')
    })
  }

  test('the data page names the agent interfaces', async ({ page }) => {
    await page.goto('/gsip/data/')
    await expect(page.getByRole('link', { name: 'Agent guide' })).toBeVisible()
    await expect(
      page.getByRole('link', { name: 'OpenAPI description' }),
    ).toHaveAttribute(
      'href',
      'https://supabase.test/functions/v1/gsip-public/v1/openapi.json',
    )
  })
})

test('the browser adopts every prerendered page without an error', async ({
  page,
}) => {
  const errors: string[] = []
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text())
  })
  page.on('pageerror', (error) => errors.push(error.message))
  for (const [path, headline] of PAGES) {
    await page.goto(`/gsip/${path}`)
    await page.waitForLoadState('networkidle')
    await expect(
      page.getByRole('heading', { level: 1, name: headline }),
    ).toBeVisible()
  }
  expect(errors).toEqual([])
})

test('llms.txt at the site root directs agents to the interfaces and terms', async ({
  request,
}) => {
  const response = await request.get('/gsip/llms.txt')
  expect(response.ok()).toBe(true)
  expect(response.headers()['content-type']).toMatch(/^text\/plain/)
  const text = await response.text()
  expect(text.startsWith('# Global Soil Intelligence Project (GSIP)\n')).toBe(
    true,
  )
  expect(text).toContain(
    '(https://supabase.test/functions/v1/gsip-public/v1/openapi.json)',
  )
  expect(text).toContain('(https://supabase.test/functions/v1/gsip-public/mcp)')
  expect(text).toContain('/docs/AGENTS.md)')
  expect(text).toMatch(/untrusted/)
  expect(text).not.toMatch(/soil[\s-]+test/i)
})
