import { cpSync, mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

const root = fileURLToPath(new URL('.', import.meta.url))
const iconsDir = fileURLToPath(new URL('./icons', import.meta.url))
const sharedDir = fileURLToPath(new URL('../shared/saral-ui', import.meta.url))

/**
 * Copies the static extension assets (manifest + toolbar icons) into the build
 * output so that `dist/` is a self-contained, loadable unpacked extension.
 */
function copyExtensionAssets(): Plugin {
  return {
    name: 'saral:copy-extension-assets',
    apply: 'build',
    closeBundle() {
      const outDir = fileURLToPath(new URL('./dist', import.meta.url))
      mkdirSync(`${outDir}/icons`, { recursive: true })
      cpSync(`${root}/manifest.json`, `${outDir}/manifest.json`)
      cpSync(iconsDir, `${outDir}/icons`, { recursive: true })
    },
  }
}

export default defineConfig({
  root,
  plugins: [react(), copyExtensionAssets()],
  resolve: {
    alias: {
      // The Markdown parser is shared with the website so both interfaces
      // render the same content in the same way.
      '@saral-ui': sharedDir,
    },
  },
  server: {
    fs: {
      allow: [fileURLToPath(new URL('..', import.meta.url))],
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    target: 'chrome116',
    sourcemap: false,
    rollupOptions: {
      input: fileURLToPath(new URL('./popup.html', import.meta.url)),
    },
  },
})
