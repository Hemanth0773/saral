import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import { formatReadingLevel } from '../../../shared/saral-ui/readability.ts';

const REPO_ROOT = fileURLToPath(new URL('../../../', import.meta.url));

function readSource(relativePath: string): string {
  return readFileSync(`${REPO_ROOT}${relativePath}`, 'utf8');
}

// ============================================================
// The reading level
// ============================================================

test('a measured grade is shown', () => {
  const label = formatReadingLevel({
    simplified: { flesch_kincaid_grade: 5.2 },
    target_grade_level: 5,
  });

  assert.equal(label, 'Reading level: Grade 5.2');
});

test('a grade below the target is reported honestly', () => {
  const label = formatReadingLevel({
    simplified: { flesch_kincaid_grade: 4.3 },
    target_grade_level: 5,
  });

  assert.equal(label, 'Reading level: Below Grade 5.0');
});

test('the target is never assumed to have been reached', () => {
  const label = formatReadingLevel({
    simplified: { flesch_kincaid_grade: 12.5 },
    target_grade_level: 5,
  });

  assert.equal(label, 'Reading level: Grade 12.5');
  assert.equal(label.includes('Below'), false);
});

test('no label is shown when the measurement is missing', () => {
  assert.equal(formatReadingLevel(null), null);
  assert.equal(formatReadingLevel(undefined), null);
  assert.equal(formatReadingLevel({ simplified: null, target_grade_level: 5 }), null);
  assert.equal(
    formatReadingLevel({ simplified: { flesch_kincaid_grade: null }, target_grade_level: 5 }),
    null,
  );
});

test('the popup does not show a placeholder grade', () => {
  const source = readSource('extension/src/popup/components/SummaryCard.tsx');

  assert.equal(source.includes('Grade not measured'), false);
  assert.equal(source.includes('not measured'), false);
});

test('the popup and the website use the same label helper', () => {
  const extension = readSource('extension/src/popup/App.tsx');
  const website = readSource('frontend/src/components/TrySaralNow.tsx');

  assert.ok(extension.includes('formatReadingLevel'));
  assert.ok(website.includes('formatReadingLevel'));
});

// ============================================================
// One scroll surface
// ============================================================

test('the summary card does not scroll on its own', () => {
  const source = readSource('extension/src/popup/components/SummaryCard.tsx');

  assert.equal(source.includes('overflow-y-auto'), false);
});

test('the popup scrolls in one place', () => {
  const source = readSource('extension/src/popup/App.tsx');

  // The main area is the single scroll surface.
  assert.ok(source.includes('overflow-y-auto'));
  const scrollAreas = source.match(/scroll-area/g) ?? [];
  assert.equal(scrollAreas.length, 1);
});

test('the output is not clipped away', () => {
  const source = readSource('extension/src/popup/components/SummaryCard.tsx');

  // The collapsed text is a preview that the button reveals.
  assert.ok(source.includes('Show full text'));
  assert.ok(source.includes('overflow-hidden'));
});

// ============================================================
// The colour swap
// ============================================================

test('the popup surface is yellow', () => {
  const styles = readSource('extension/src/styles/index.css');

  assert.ok(styles.includes('background-color: #f9c915'), 'the body must be yellow');
  assert.equal(styles.includes('background-color: #fbf8fc'), false);
});

test('the cards are white', () => {
  const hero = readSource('extension/src/popup/components/HeroCard.tsx');
  const input = readSource('extension/src/popup/components/InputCard.tsx');
  const facts = readSource('extension/src/popup/components/FactList.tsx');
  const summary = readSource('extension/src/popup/components/SummaryCard.tsx');
  const audio = readSource('extension/src/popup/components/AudioDeck.tsx');

  for (const source of [hero, input, facts, summary, audio]) {
    assert.equal(source.includes('bg-saral-lavender'), false, 'an inner box must not stay lavender');
    assert.equal(source.includes('bg-saral-charcoal'), false, 'a panel must not stay dark');
  }
  assert.ok(hero.includes('bg-white'), 'the hero card must be white');
});

test('the outer corners are rounded', () => {
  const styles = readSource('extension/src/styles/index.css');
  const app = readSource('extension/src/popup/App.tsx');

  assert.ok(styles.includes('border-radius: 12px'));
  assert.ok(app.includes('rounded-xl'));
});

// ============================================================
// Safe rendering
// ============================================================

test('the popup never injects model output as HTML', () => {
  const components = [
    'extension/src/popup/components/Markdown.tsx',
    'extension/src/popup/components/SummaryCard.tsx',
    'extension/src/popup/components/FactList.tsx',
    'frontend/src/components/SimplifiedMarkdown.tsx',
  ];

  for (const component of components) {
    const source = readSource(component);
    assert.equal(source.includes('dangerouslySetInnerHTML'), false, component);
    assert.equal(source.includes('innerHTML'), false, component);
  }
});
