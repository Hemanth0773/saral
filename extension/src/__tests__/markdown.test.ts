import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import { hasMarkdown, normaliseMarkdown, parseInline, parseMarkdown } from '../popup/markdown.ts';

const SOURCE_ROOT = fileURLToPath(new URL('../', import.meta.url));

/**
 * The popup components are written in TSX, which the Node test runner cannot
 * import directly. These checks read the source instead, which is enough to
 * pin down the two properties that must not regress:
 *  - the model output is never injected as HTML,
 *  - a fact label is rendered exactly once.
 */
function readSource(relativePath: string): string {
  return readFileSync(`${SOURCE_ROOT}${relativePath}`, 'utf8');
}

// ============================================================
// Escape artefacts
// ============================================================

test('escaped bold markers are unescaped', () => {
  assert.equal(normaliseMarkdown('\\*\\*Documents needed\\*\\*'), '**Documents needed**');
  assert.equal(normaliseMarkdown('a \\- b'), 'a - b');
  assert.equal(normaliseMarkdown('\\_italic\\_'), '_italic_');
});

test('numeric HTML entities are decoded', () => {
  assert.equal(normaliseMarkdown('The&#x20;applicant'), 'The applicant');
  assert.equal(normaliseMarkdown('a&#32;b'), 'a b');
  assert.equal(normaliseMarkdown('&amp;'), '&');
  assert.equal(normaliseMarkdown('&lt;tag&gt;'), '<tag>');
  assert.equal(normaliseMarkdown('&nbsp;'), ' ');
});

test('unknown entities are left alone', () => {
  assert.equal(normaliseMarkdown('&notarealentity;'), '&notarealentity;');
  assert.equal(normaliseMarkdown('&#xZZ;'), '&#xZZ;');
});

test('line endings are normalised', () => {
  assert.equal(normaliseMarkdown('a\r\nb\rc'), 'a\nb\nc');
});

test('plain text is not changed by the normalisation', () => {
  const text = 'Students must apply annually through the National e-Scholarship Portal.';
  assert.equal(normaliseMarkdown(text), text);
});

// ============================================================
// Block parsing
// ============================================================

test('plain text becomes a single paragraph', () => {
  const blocks = parseMarkdown('Students must apply every year.');
  assert.equal(blocks.length, 1);
  assert.equal(blocks[0].kind, 'paragraph');
  if (blocks[0].kind === 'paragraph') {
    assert.equal(blocks[0].value, 'Students must apply every year.');
  }
});

test('consecutive lines are joined into one paragraph', () => {
  const blocks = parseMarkdown('First line.\nSecond line.');
  assert.equal(blocks.length, 1);
  if (blocks[0].kind === 'paragraph') {
    assert.equal(blocks[0].value, 'First line. Second line.');
  }
});

test('blank lines separate paragraphs', () => {
  const blocks = parseMarkdown('First.\n\nSecond.');
  assert.equal(blocks.length, 2);
  assert.deepEqual(
    blocks.map((block) => block.kind),
    ['paragraph', 'paragraph'],
  );
});

test('headings are recognised', () => {
  const blocks = parseMarkdown('## Documents needed\nText.');
  assert.equal(blocks[0].kind, 'heading');
  if (blocks[0].kind === 'heading') {
    assert.equal(blocks[0].level, 2);
    assert.equal(blocks[0].value, 'Documents needed');
  }
});

test('unordered lists are recognised', () => {
  const blocks = parseMarkdown('- Upload the certificate\n- Send the bank passbook');
  assert.equal(blocks.length, 1);
  assert.equal(blocks[0].kind, 'list');
  if (blocks[0].kind === 'list') {
    assert.equal(blocks[0].ordered, false);
    assert.deepEqual(blocks[0].items, ['Upload the certificate', 'Send the bank passbook']);
  }
});

test('ordered lists are recognised', () => {
  const blocks = parseMarkdown('1. Apply on the portal\n2. Upload the documents');
  assert.equal(blocks[0].kind, 'list');
  if (blocks[0].kind === 'list') {
    assert.equal(blocks[0].ordered, true);
    assert.deepEqual(blocks[0].items, ['Apply on the portal', 'Upload the documents']);
  }
});

test('a list followed by a paragraph produces two blocks', () => {
  const blocks = parseMarkdown('- one\n- two\n\nA closing note.');
  assert.equal(blocks.length, 2);
  assert.equal(blocks[0].kind, 'list');
  assert.equal(blocks[1].kind, 'paragraph');
});

test('fenced code blocks are kept as code', () => {
  const blocks = parseMarkdown('```\nline one\nline two\n```');
  assert.equal(blocks.length, 1);
  assert.equal(blocks[0].kind, 'code');
  if (blocks[0].kind === 'code') {
    assert.equal(blocks[0].value, 'line one\nline two');
  }
});

test('hasMarkdown only reports real markup', () => {
  assert.equal(hasMarkdown('Plain text with no markup.'), false);
  assert.equal(hasMarkdown('**Bold** text'), true);
  assert.equal(hasMarkdown('- a list'), true);
});

// ============================================================
// Inline parsing
// ============================================================

test('bold text is parsed as bold', () => {
  const nodes = parseInline('**Documents needed**: Aadhaar');
  assert.equal(nodes[0].kind, 'bold');
  if (nodes[0].kind === 'bold') {
    assert.equal(nodes[0].value, 'Documents needed');
  }
  assert.equal(nodes[nodes.length - 1].kind, 'text');
});

test('italic text is parsed as italic', () => {
  const nodes = parseInline('*normally* announced');
  assert.equal(nodes[0].kind, 'italic');
});

test('inline code is parsed as code', () => {
  const nodes = parseInline('use the `portal` link');
  assert.ok(nodes.some((node) => node.kind === 'code'));
});

test('a lone asterisk is not treated as emphasis', () => {
  const nodes = parseInline('5 * 3 = 15');
  assert.ok(nodes.every((node) => node.kind === 'text'));
});

// ============================================================
// Security
// ============================================================

test('HTML in the model output stays text', () => {
  const blocks = parseMarkdown('<script>alert(1)</script>');
  assert.equal(blocks[0].kind, 'paragraph');
  if (blocks[0].kind === 'paragraph') {
    assert.equal(blocks[0].value, '<script>alert(1)</script>');
  }
});

test('an image with an event handler stays text', () => {
  const blocks = parseMarkdown('<img src=x onerror="alert(1)">');
  if (blocks[0].kind === 'paragraph') {
    assert.ok(blocks[0].value.includes('onerror'));
  }
});

test('a javascript link stays text', () => {
  const blocks = parseMarkdown('[click me](javascript:alert(1))');
  const rendered = JSON.stringify(blocks);
  assert.ok(rendered.includes('javascript:alert(1)'));
});

test('the popup never injects model output as HTML', () => {
  const components = [
    'popup/components/Markdown.tsx',
    'popup/components/SummaryCard.tsx',
    'popup/components/FactList.tsx',
  ];

  for (const component of components) {
    const source = readSource(component);
    assert.equal(
      source.includes('dangerouslySetInnerHTML'),
      false,
      `${component} must not use dangerouslySetInnerHTML`,
    );
    assert.equal(source.includes('innerHTML'), false, `${component} must not use innerHTML`);
  }
});

test('a fact label is rendered exactly once', () => {
  const source = readSource('popup/components/FactList.tsx');
  const occurrences = source.split('{fact.label}').length - 1;
  assert.equal(
    occurrences,
    1,
    'the label must be rendered once, not duplicated as a screen-reader-only prefix',
  );
});
