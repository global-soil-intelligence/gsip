import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig(({ mode }) => ({
  base: './',
  plugins: [
    react(),
    mode !== 'native' &&
      VitePWA({
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
        workbox: { maximumFileSizeToCacheInBytes: 3000000 },
        registerType: 'autoUpdate',
      }),
  ],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
  },
}))
