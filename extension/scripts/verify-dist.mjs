/**
 * Verifies that the built extension folder is self-consistent and loadable:
 * every path the manifest references must exist inside `dist/`.
 *
 * Usage: node scripts/verify-dist.mjs
 */
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const dist = path.resolve(fileURLToPath(new URL('../dist', import.meta.url)));
const manifestPath = path.join(dist, 'manifest.json');

let ok = true;

function check(label, relativePath) {
  const full = path.join(dist, relativePath);
  const exists = existsSync(full);
  if (!exists) ok = false;
  console.log(`${exists ? '  OK  ' : ' MISS '} ${label} -> ${relativePath}`);
}

if (!existsSync(manifestPath)) {
  console.error('dist/manifest.json is missing. Run `npm run build` first.');
  process.exit(1);
}

const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));

console.log(`manifest_version = ${manifest.manifest_version}`);
console.log(`name             = ${manifest.name}`);
console.log(`version          = ${manifest.version}`);
console.log('');

if (manifest.manifest_version !== 3) {
  console.error('manifest_version must be 3');
  ok = false;
}

check('popup', manifest.action.default_popup);
check('service worker', manifest.background.service_worker);

for (const [size, icon] of Object.entries(manifest.icons ?? {})) {
  check(`icon ${size}`, icon);
}
for (const [size, icon] of Object.entries(manifest.action?.default_icon ?? {})) {
  check(`action icon ${size}`, icon);
}

const html = readFileSync(path.join(dist, manifest.action.default_popup), 'utf8');
for (const match of html.matchAll(/(?:src|href)="([^"]+)"/g)) {
  const url = match[1];
  if (url.startsWith('/')) check('popup asset', url.slice(1));
}

// The content script is injected by the service worker.
const background = readFileSync(path.join(dist, manifest.background.service_worker), 'utf8');
const injected = background.match(/files:\s*\[([^\]]+)\]/);
if (injected) {
  const file = injected[1].replace(/['"`\s]/g, '');
  check('injected content script', file);
} else {
  console.log(' MISS  could not find the injected content script reference');
  ok = false;
}

// The bundled help page is opened from the popup footer.
check('help page', 'help.html');

console.log('');
console.log('permissions               =', JSON.stringify(manifest.permissions));
console.log('host_permissions          =', JSON.stringify(manifest.host_permissions));
console.log('optional_host_permissions =', JSON.stringify(manifest.optional_host_permissions));
console.log('commands                  =', JSON.stringify(Object.keys(manifest.commands ?? {})));
console.log('');

console.log(ok ? 'DIST IS SELF-CONSISTENT' : 'DIST HAS MISSING FILES');
process.exit(ok ? 0 : 1);
