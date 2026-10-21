import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const REPO_ROOT = fileURLToPath(new URL('../../../', import.meta.url));

function readSource(relativePath: string): string {
  return readFileSync(`${REPO_ROOT}${relativePath}`, 'utf8');
}

function readJson(relativePath: string): Record<string, unknown> {
  return JSON.parse(readSource(relativePath));
}

// ============================================================
// The reading level label is gone
// ============================================================

test('the popup does not show a reading level', () => {
  const summary = readSource('extension/src/popup/components/SummaryCard.tsx');
  const app = readSource('extension/src/popup/App.tsx');

  assert.equal(summary.includes('Reading level'), false);
  assert.equal(summary.includes('gradeLabel'), false);
  assert.equal(app.includes('formatReadingLevel'), false);
  assert.equal(app.includes('gradeLabel'), false);
});

test('the website does not show a reading level', () => {
  const website = readSource('frontend/src/components/TrySaralNow.tsx');

  assert.equal(website.includes('Reading level'), false);
  assert.equal(website.includes('formatReadingLevel'), false);
  assert.equal(website.includes('readingLevel'), false);
});

test('the popup does not show a placeholder grade', () => {
  const source = readSource('extension/src/popup/components/SummaryCard.tsx');

  assert.equal(source.includes('Grade not measured'), false);
  assert.equal(source.includes('not measured'), false);
});

test('the backend still measures the readability', () => {
  // The measurement stays available in the API, it is simply not shown.
  const source = readSource('backend/app/services/readability_service.py');

  assert.ok(source.includes('flesch_kincaid_grade'));
  assert.ok(source.includes('flesch_reading_ease'));
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
// The outer corners
// ============================================================

test('the popup surface is yellow', () => {
  const styles = readSource('extension/src/styles/index.css');

  assert.ok(styles.includes('background-color: #f9c915'), 'the body must be yellow');
  assert.equal(styles.includes('background-color: #fbf8fc'), false);
});

test('the canvas behind the popup has its own background', () => {
  const styles = readSource('extension/src/styles/index.css');

  // Without a background on the html element the browser paints the body
  // background over the whole window and the rounded corners are lost.
  const htmlRule = styles.slice(styles.indexOf('html {'), styles.indexOf('body {'));
  assert.ok(htmlRule.includes('background-color'), 'the html element needs its own background');
});

test('the popup surface and its content share one radius', () => {
  const styles = readSource('extension/src/styles/index.css');
  const app = readSource('extension/src/popup/App.tsx');

  assert.ok(styles.includes('border-radius: 12px'));
  assert.ok(app.includes('rounded-xl'), 'the popup container must be rounded');
  // The content is clipped to the radius, so the header corners follow it.
  assert.ok(app.includes('overflow-hidden'));
});

test('the canvas behind the popup is transparent', () => {
  const styles = readSource('extension/src/styles/index.css');

  // A white canvas shows through the rounded corners of the yellow popup
  // surface as four white square edges.
  const htmlRule = styles.slice(styles.indexOf('html {'), styles.indexOf('body {'));
  assert.ok(htmlRule.includes('background-color'), 'the html element needs a background');
  assert.equal(htmlRule.includes('#ffffff'), false, 'the canvas must not be white');
  assert.ok(htmlRule.includes('transparent'));
});

test('the popup surface is yellow and rounded', () => {
  const styles = readSource('extension/src/styles/index.css');
  const bodyRule = styles.slice(styles.indexOf('body {'), styles.indexOf('button,'));

  assert.ok(bodyRule.includes('background-color: #f9c915'), 'the popup surface is yellow');
  assert.ok(bodyRule.includes('border-radius: 12px'), 'the popup surface is rounded');
  assert.ok(bodyRule.includes('overflow: hidden'), 'the content is clipped to the radius');
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

// ============================================================
// The Help & Docs link
// ============================================================

test('the Help & Docs link does not turn yellow on hover', () => {
  const footer = readSource('extension/src/popup/components/Footer.tsx');

  // The popup background is yellow, so yellow text would disappear.
  assert.equal(footer.includes('hover:text-saral-yellow'), false);
  assert.equal(footer.includes('hover:bg-saral-yellow'), false);
  assert.equal(footer.includes('text-saral-yellow'), false);
});

test('the Help & Docs link keeps its dark text and an underline', () => {
  const footer = readSource('extension/src/popup/components/Footer.tsx');

  assert.ok(footer.includes('text-saral-ink'), 'the text stays dark');
  assert.ok(footer.includes('underline'), 'the link is underlined');
  assert.ok(footer.includes('hover:decoration-saral-ink'), 'the underline strengthens on hover');
  assert.ok(footer.includes('focus-ring'), 'keyboard focus stays visible');
  assert.ok(footer.includes('onClick={onOpenHelp}'), 'the link still opens the help page');
  assert.ok(footer.includes('ExternalLinkIcon'), 'the external link icon is kept');
});

// ============================================================
// The keyboard shortcut
// ============================================================

test('the manifest registers the shortcut with the reserved action command', () => {
  const manifest = readJson('extension/manifest.json');
  const commands = manifest.commands as Record<string, { suggested_key?: { default?: string }; description?: string }>;

  // "_execute_action" is handled by Chrome itself, which opens the popup
  // reliably. A custom command relies on chrome.action.openPopup(), which
  // Chrome only allows in some situations.
  assert.ok(commands._execute_action, 'the reserved action command must be registered');
  assert.equal(commands._execute_action.suggested_key?.default, 'Alt+S');
  assert.equal(commands._execute_action.description, 'Open Saral on any page');
});

test('the footer advertises the shortcut that is registered', () => {
  const footer = readSource('extension/src/popup/components/Footer.tsx');
  const manifest = readJson('extension/manifest.json');
  const commands = manifest.commands as Record<string, { suggested_key?: { default?: string } }>;

  assert.ok(footer.includes('Alt+S'));
  assert.equal(commands._execute_action.suggested_key?.default, 'Alt+S');
});

test('the service worker opens the popup for the fallback command', async () => {
  const listeners: ((command: string) => void)[] = [];
  let opened = 0;

  const scope = globalThis as unknown as { chrome: unknown };
  scope.chrome = {
    commands: {
      onCommand: {
        addListener: (listener: (command: string) => void) => listeners.push(listener),
      },
    },
    action: {
      openPopup: async () => {
        opened += 1;
      },
    },
    runtime: {
      onMessage: { addListener: () => undefined },
    },
  };

  // A unique query string keeps this import out of the module cache.
  await import(`../background/index.ts?shortcut-test=${Date.now()}`);

  assert.equal(listeners.length, 1, 'the service worker must listen for commands');

  listeners[0]('some-other-command');
  assert.equal(opened, 0, 'another command must not open the popup');

  listeners[0]('read-active-tab');
  assert.equal(opened, 1, 'the fallback command must open the popup');
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
