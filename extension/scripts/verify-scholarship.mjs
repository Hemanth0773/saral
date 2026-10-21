/**
 * End-to-end check: the real backend response for the scholarship notice,
 * run through the real extension fact derivation and Markdown parser.
 */
import { readFileSync } from 'node:fs';
import { toFactItem } from '../src/shared/facts.ts';
import { normaliseMarkdown, parseMarkdown } from '../../shared/saral-ui/markdown.ts';

const BASE = process.env.SARAL_BASE_URL ?? 'http://127.0.0.1:8000';

// The complete notice used by the backend regression tests.
const NOTICE = readFileSync(
  new URL('../../backend/tests/fixtures/scholarship_terms.txt', import.meta.url),
  'utf8',
);

async function post(path, body) {
  const response = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(`${path} -> ${response.status} ${JSON.stringify(payload).slice(0, 300)}`);
  }
  return payload.data ?? payload;
}

const simplification = await post('/api/documents/simplify', {
  text: NOTICE,
  target_grade_level: 5,
});
// The backend builds the canonical summary, so the website and the extension
// render exactly the same facts.
const summary = (simplification.instant_summary ?? []).map(toFactItem);

console.log('=== INSTANT SUMMARY BULLETS (as the popup renders them) ===');
for (const fact of summary) {
  console.log(`  ${fact.label}: ${fact.value}`);
}
console.log(
  `  (${simplification.metadata?.summary_total ?? summary.length} facts found, ` +
    `${simplification.metadata?.summary_hidden ?? 0} hidden)`,
);

console.log('\n=== MALFORMED PATTERN CHECK ===');
const rendered = summary.map((fact) => `${fact.label}: ${fact.value}`).join('\n');
const checks = {
  'duplicated label (Label:Label:)': /(\w[\w ]*):\1:/i.test(rendered),
  'page marker as a fact': /page\s+\d+/i.test(rendered),
  'heading as a fact': /PROCEDURE FOR AVAILING/.test(rendered),
  'fragment starting with punctuation': /^[^:]*: [,;]/m.test(rendered),
  'age direction lost (30+ instead of below 30)': /\b30\+ years/.test(rendered),
  'a positive eligibility rule for a negative rule':
    /Eligibility:[^\n]*not eligible/i.test(rendered),
};
for (const [name, failed] of Object.entries(checks)) {
  console.log(`  ${failed ? 'PROBLEM' : 'ok'}: ${name}`);
}

console.log('\n=== SIMPLIFIED TEXT (Markdown) ===');
console.log(simplification.simplified_text.slice(0, 600));
console.log('\n=== PARSED BLOCKS ===');
for (const block of parseMarkdown(simplification.simplified_text)) {
  console.log(`  ${block.kind}: ${JSON.stringify(block).slice(0, 140)}`);
}

console.log('\n=== ESCAPE ARTEFACT CHECK ===');
const normalised = normaliseMarkdown(simplification.simplified_text);
for (const token of ['\\*\\*', '\\-', '&#x20;', '&amp;', '\\_']) {
  console.log(`  ${JSON.stringify(token)} -> ${normalised.split(token).length - 1}`);
}
console.log('  literal ** count ->', (normalised.match(/\*\*/g) ?? []).length);
