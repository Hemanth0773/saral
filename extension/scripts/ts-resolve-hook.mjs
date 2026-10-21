/**
 * Module resolution hook for the extension's test suite.
 *
 * The extension source uses extension-less relative imports (the idiomatic
 * Vite style). Node's ESM resolver requires explicit file extensions, so this
 * hook maps `./foo` to `./foo.ts` / `./foo.tsx` when running the tests with
 * `node --test`. It only affects the test runner — the production build is
 * handled by Vite.
 */
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const CANDIDATE_SUFFIXES = ['.ts', '.tsx', '.mts', '.js'];
const CANDIDATE_INDEXES = ['index.ts', 'index.tsx'];

export async function resolve(specifier, context, nextResolve) {
  const isRelative = specifier.startsWith('./') || specifier.startsWith('../');
  const hasExtension = /\.[a-zA-Z0-9]+$/.test(specifier);

  if (isRelative && !hasExtension && context.parentURL) {
    const baseDir = path.dirname(fileURLToPath(context.parentURL));
    const target = path.resolve(baseDir, specifier);

    for (const suffix of CANDIDATE_SUFFIXES) {
      const candidate = `${target}${suffix}`;
      if (existsSync(candidate)) {
        return nextResolve(pathToFileURL(candidate).href, context);
      }
    }

    for (const index of CANDIDATE_INDEXES) {
      const candidate = path.join(target, index);
      if (existsSync(candidate)) {
        return nextResolve(pathToFileURL(candidate).href, context);
      }
    }
  }

  return nextResolve(specifier, context);
}
