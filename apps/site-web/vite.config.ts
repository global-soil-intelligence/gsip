import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  base: './',
  build: {
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
})
