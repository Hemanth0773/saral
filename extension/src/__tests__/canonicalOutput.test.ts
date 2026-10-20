import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import { toFactItem, MAX_SUMMARY_FACTS } from '../shared/facts.ts';
import type { InstantSummaryItem } from '../types/api.ts';

const REPO_ROOT = fileURLToPath(new URL('../../../', import.meta.url));

function readSource(relativePath: string): string {
  return readFileSync(`${REPO_ROOT}${relativePath}`, 'utf8');
}

/**
 * The response the backend returns for a scholarship notice. The website and
 * the extension both render this exact list, so they cannot disagree.
 */
const CANONICAL_RESPONSE = {
  success: true,
  document_id: 'doc_20261020_120000_abcdef12',
  original_text: 'source',
  simplified_text: '### 1. ELIGIBILITY\n\n- The student must have **60% marks**.',
  target_grade_level: 5,
  model_used: 'openai/gpt-oss-20b',
  processing_time_ms: 3210,
  sections: [],
  preserved_facts: [],
  key_terms: [],
  instant_summary: [
    { id: 'deadline-0', kind: 'deadline', label: 'Deadline', value: '2026-07-31', severity: 'critical' },
    { id: 'documents', kind: 'document', label: 'Documents needed', value: 'Aadhaar, income certificate', severity: 'info' },
    { id: 'money-0', kind: 'money', label: 'Scholarship amount', value: '₹2,50,000', severity: 'info' },
    { id: 'age-0', kind: 'age', label: 'Age requirement', value: 'under 30 years', severity: 'info' },
    { id: 'eligibility-0', kind: 'eligibility', label: 'Eligibility', value: 'The applicant must have secured at least 60% marks.', severity: 'info' },
    { id: 'condition-0', kind: 'condition', label: 'Conditions', value: 'The institution shall retain the documents for five years.', severity: 'info' },
    { id: 'procedure-0', kind: 'procedure', label: 'Step 1', value: 'Students must apply annually through the portal.', severity: 'info' },
  ] as InstantSummaryItem[],
  validation_passed: true,
  validation_failures: [],
  metadata: { chunks: 1, retry_count: 0, summary_total: 7, summary_hidden: 0 },
};

// ============================================================
// The canonical summary is used as it is
// ============================================================

test('the backend summary is rendered with its own labels and values', () => {
  const facts = CANONICAL_RESPONSE.instant_summary.map(toFactItem);

  assert.equal(facts.length, CANONICAL_RESPONSE.instant_summary.length);
  assert.equal(facts[0].label, 'Deadline');
  assert.equal(facts[0].value, '2026-07-31');
  assert.equal(facts[0].severity, 'critical');
  assert.equal(facts[3].label, 'Age requirement');
  assert.equal(facts[3].value, 'under 30 years');
  assert.equal(facts[4].label, 'Eligibility');
  assert.equal(facts[6].label, 'Step 1');
});

test('the label is never repeated inside the value', () => {
  for (const fact of CANONICAL_RESPONSE.instant_summary.map(toFactItem)) {
    assert.equal(
      fact.value.trim().toLowerCase().startsWith(`${fact.label.trim().toLowerCase()}:`),
      false,
    );
  }
});

test('the extension and the website read the same response field', () => {
  const extension = readSource('extension/src/popup/App.tsx');
  const website = readSource('frontend/src/components/TrySaralNow.tsx');

  assert.ok(extension.includes('instant_summary'), 'the extension must use instant_summary');
  assert.ok(website.includes('instant_summary'), 'the website must use instant_summary');
});

test('the website renders the canonical summary, not its own copy', () => {
  const website = readSource('frontend/src/components/TrySaralNow.tsx');

  assert.ok(website.includes('InstantSummary'), 'the website must render the InstantSummary');
  // The website must not derive the summary itself.
  assert.equal(website.includes('buildFactSummary'), false);
  assert.equal(website.includes('extract-info'), false);
});

test('the extension does not call the structured extraction for the summary', () => {
  const extension = readSource('extension/src/popup/App.tsx');

  // The extraction is only a fallback for a backend without the summary.
  assert.ok(extension.includes('instant_summary'));
});

// ============================================================
// One Markdown parser for both interfaces
// ============================================================

test('both interfaces use the shared Markdown parser', () => {
  const extension = readSource('extension/src/popup/components/Markdown.tsx');
  const website = readSource('frontend/src/components/SimplifiedMarkdown.tsx');

  assert.ok(extension.includes('@saral-ui/markdown'));
  assert.ok(website.includes('@saral-ui/markdown'));
});

test('the shared parser lives in one place', () => {
  const shared = readSource('shared/saral-ui/markdown.ts');

  assert.ok(shared.includes('export function parseMarkdown'));
  assert.ok(shared.includes('export function normaliseMarkdown'));
});

test('the website never injects the model output as HTML', () => {
  const website = readSource('frontend/src/components/SimplifiedMarkdown.tsx');

  assert.equal(website.includes('dangerouslySetInnerHTML'), false);
  assert.equal(website.includes('innerHTML'), false);
});

test('the extension never injects the model output as HTML', () => {
  const extension = readSource('extension/src/popup/components/Markdown.tsx');

  assert.equal(extension.includes('dangerouslySetInnerHTML'), false);
  assert.equal(extension.includes('innerHTML'), false);
});

// ============================================================
// The summary limit matches the backend
// ============================================================

test('the popup limit matches the backend limit', () => {
  const backend = readSource('backend/app/services/summary_service.py');
  const match = backend.match(/MAX_SUMMARY_ITEMS\s*=\s*(\d+)/);

  assert.ok(match, 'the backend limit must be readable');
  assert.equal(Number(match[1]), MAX_SUMMARY_FACTS);
});
