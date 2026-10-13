import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  use: { baseURL: 'http://127.0.0.1:4173', trace: 'retain-on-failure' },
  webServer: {
    command: 'uv run python tests/e2e_server.py',
    reuseExistingServer: false,
    url: 'http://127.0.0.1:4173/gsip/',
  },
  projects: [
    { name: 'mobile-chrome', use: { ...devices['Pixel 7'] } },
    {
      name: 'mobile-safari',
      use: { ...devices['iPhone 15'], serviceWorkers: 'block' },
    },
    { name: 'desktop-chrome', use: { ...devices['Desktop Chrome'] } },
  ],
})
