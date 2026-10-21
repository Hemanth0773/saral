import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // The Markdown parser is shared with the Chrome extension so both
      // interfaces render the same content in the same way.
      '@saral-ui': fileURLToPath(new URL('../shared/saral-ui', import.meta.url)),
    },
  },
  server: {
    port: 3000,
    strictPort: true,
    fs: {
      allow: [fileURLToPath(new URL('..', import.meta.url))],
    },
  },
})
