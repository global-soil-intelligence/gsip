import react from '@vitejs/plugin-react'
import { loadEnv } from 'vite'
import { defineConfig } from 'vitest/config'
import { VitePWA } from 'vite-plugin-pwa'
import packageJson from './package.json' with { type: 'json' }

export default defineConfig(({ mode }) => {
  // WP-6e (I10): the build's software version, sent with every observation as a claim. CI builds
  // add the commit they were built from.
  const sha = (loadEnv(mode, '.', 'GITHUB_').GITHUB_SHA ?? '').slice(0, 7)
  const clientVersion = /^[0-9a-f]{7}$/.test(sha)
    ? `${packageJson.version}+${sha}`
    : packageJson.version
  // WP-APP-1: `vite build --mode app` builds the phone app's assets. They ship inside the app,
  // so there is no service worker: one would keep serving an old version after an app update.
  const app = mode === 'app'
  return {
    base: './',
    define: { __GSIP_CLIENT_VERSION__: JSON.stringify(clientVersion) },
    plugins: [
      react(),
      VitePWA({
        disable: app,
        manifest: {
          name: 'GSIP Soil Capture',
          short_name: 'GSIP Capture',
          description: 'Contribute privacy-safe soil observations.',
          display: 'standalone',
          start_url: './',
          theme_color: '#123c2d',
          background_color: '#f4f0e5',
          icons: [
            {
              src: 'icon.svg',
              sizes: 'any',
              type: 'image/svg+xml',
              purpose: 'any maskable',
            },
          ],
        },
        registerType: 'autoUpdate',
      }),
    ],
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: ['./tests/setup.ts'],
    },
  }
})
