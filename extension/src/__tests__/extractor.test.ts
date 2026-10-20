import test from 'node:test';
import assert from 'node:assert/strict';

import {
  MAIN_CONTENT_SELECTORS,
  MIN_SELECTION_LENGTH,
  NOISE_SELECTORS,
  cleanExtractedText,
  pickExtractionSource,
  truncateText,
} from '../content/extractor.ts';

test('cleanExtractedText collapses whitespace but keeps paragraph breaks', () => {
  const raw = '  First   paragraph.\n\n\n\nSecond   paragraph.  \n   ';
  assert.equal(cleanExtractedText(raw), 'First paragraph.\n\nSecond paragraph.');
});

test('cleanExtractedText removes non-breaking spaces and zero width characters', () => {
  assert.equal(cleanExtractedText('a\u00a0b\u200bc'), 'a b c');
});

test('cleanExtractedText trims trailing whitespace on every line', () => {
  assert.equal(cleanExtractedText('one  \ntwo  '), 'one\ntwo');
});

test('truncateText leaves short text untouched', () => {
  const result = truncateText('short text', 100);
  assert.equal(result.truncated, false);
  assert.equal(result.text, 'short text');
});

test('truncateText cuts long text at a paragraph break when possible', () => {
  const text = `${'a'.repeat(60)}\n${'b'.repeat(60)}`;
  const result = truncateText(text, 80);
  assert.equal(result.truncated, true);
  assert.ok(result.text.length <= 80);
  assert.ok(!result.text.includes('b'));
});

test('truncateText reports when content was dropped', () => {
  const result = truncateText('x'.repeat(200), 50);
  assert.equal(result.truncated, true);
  assert.equal(result.text.length, 50);
});

test('a real selection wins over the page content', () => {
  const picked = pickExtractionSource('the selected paragraph', 'the whole page text');
  assert.equal(picked.source, 'selection');
  assert.equal(picked.text, 'the selected paragraph');
});

test('an empty selection falls back to the page content', () => {
  const picked = pickExtractionSource('   ', 'the whole page text');
  assert.equal(picked.source, 'page');
  assert.equal(picked.text, 'the whole page text');
});

test('a tiny accidental selection is ignored', () => {
  const picked = pickExtractionSource('a', 'the whole page text');
  assert.equal(picked.source, 'page');
  assert.equal(MIN_SELECTION_LENGTH, 3);
});

test('the main content selectors cover the common semantic containers', () => {
  for (const selector of ['main', 'article', '[role="main"]']) {
    assert.ok(MAIN_CONTENT_SELECTORS.includes(selector), `missing ${selector}`);
  }
});

test('the noise selectors strip navigation, boilerplate and ads', () => {
  for (const selector of ['nav', 'footer', 'script', 'style', 'aside', 'form']) {
    assert.ok(NOISE_SELECTORS.includes(selector), `missing ${selector}`);
  }
  assert.ok(NOISE_SELECTORS.some((selector) => selector.includes('cookie')));
  assert.ok(NOISE_SELECTORS.some((selector) => selector.includes('advert')));
});
