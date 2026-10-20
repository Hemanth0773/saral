import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'

/**
 * Builds one of the two non-React extension entry points as a standalone IIFE
 * bundle.
 *
 * IIFE output matters: content scripts are loaded by Chrome as classic scripts
 * and therefore cannot contain `import`/`export` statements. Each entry is
 * built on its own because Rollup does not allow several IIFE entry points in
 * a single build, and because each script runs in its own isolated context.
 *
 * Usage:
 *   vite build --config vite.scripts.config.ts --mode background
 *   vite build --config vite.scripts.config.ts --mode content
 */
export default defineConfig(({ mode }) => {
  const entryName = mode === 'content' ? 'content' : 'background'
  const entryFile =
    entryName === 'content'
      ? fileURLToPath(new URL('./src/content/index.ts', import.meta.url))
      : fileURLToPath(new URL('./src/background/index.ts', import.meta.url))

  return {
    root: fileURLToPath(new URL('.', import.meta.url)),
    publicDir: false,
    define: {
      'process.env.NODE_ENV': JSON.stringify('production'),
    },
    build: {
      outDir: 'dist',
      emptyOutDir: false,
      target: 'chrome116',
      sourcemap: false,
      lib: {
        entry: entryFile,
        formats: ['iife'],
        name: 'SaralExt',
        fileName: () => `${entryName}.js`,
      },
    },
  }
})
