import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig(({ isSsrBuild }) => ({
  base: './',
  build: isSsrBuild
    ? // The prerender bundle (scripts/prerender.mjs) only renders HTML; it ships nowhere.
      { copyPublicDir: false, outDir: 'dist-ssr' }
    : {
        rollupOptions: {
          input: {
            about: 'about/index.html',
            card: 'card/index.html',
            data: 'data/index.html',
            home: 'index.html',
            methods: 'methods/index.html',
          },
        },
      },
  plugins: [react()],
  test: { environment: 'jsdom', globals: true },
}))
