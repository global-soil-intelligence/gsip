import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  use: { baseURL: 'http://127.0.0.1:4173', trace: 'retain-on-failure' },
  webServer: {
    command: 'pnpm build:pages && node scripts/serve-pages.mjs',
    env: {
      VITE_SUPABASE_PUBLISHABLE_KEY: 'e2e-publishable-key',
      VITE_SUPABASE_URL: 'https://supabase.test',
    },
    reuseExistingServer: true,
    url: 'http://127.0.0.1:4173/gsip/',
  },
  projects: [
    { name: 'mobile-chrome', use: { ...devices['Pixel 7'] } },
    { name: 'mobile-safari', use: { ...devices['iPhone 15'] } },
    { name: 'desktop-chrome', use: { ...devices['Desktop Chrome'] } },
  ],
})
