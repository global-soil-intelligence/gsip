import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  base: './',
  build: { license: { fileName: 'THIRD_PARTY_LICENSES.md' } },
  plugins: [react()],
  test: { environment: 'jsdom', globals: true },
})
