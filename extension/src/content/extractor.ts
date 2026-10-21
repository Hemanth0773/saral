/**
 * Readable-content extraction for the current page.
 *
 * The strategy is deliberately generic (no government-site-specific rules):
 *  1. prefer an explicit text selection made by the user,
 *  2. otherwise prefer a semantic main container (`main`, `article`,
 *     `[role="main"]`, common content wrappers),
 *  3. otherwise fall back to the body minus navigation / boilerplate.
 *
 * Boilerplate (nav, header, footer, sidebars, cookie banners, ads, scripts,
 * hidden nodes) is stripped before the text is read.
 */
import type { ExtractedContent } from '../types/messages';

/** Minimum characters for a selection to count as an intentional selection. */
export const MIN_SELECTION_LENGTH = 3;

/** Containers that usually hold the article body, in priority order. */
export const MAIN_CONTENT_SELECTORS = [
  'main',
  'article',
  '[role="main"]',
  '#main',
  '#content',
  '#main-content',
  '.main-content',
  '.main_content',
  '.content-wrapper',
  '.page-content',
  '.post-content',
  '.entry-content',
  '.article-content',
  '.article-body',
  '.content-body',
];

/** Boilerplate that must never reach the backend. */
export const NOISE_SELECTORS = [
  'script',
  'style',
  'noscript',
  'template',
  'iframe',
  'object',
  'embed',
  'canvas',
  'svg',
  'form',
  'button',
  'input',
  'select',
  'textarea',
  'nav',
  'aside',
  'footer',
  '[role="navigation"]',
  '[role="banner"]',
  '[role="contentinfo"]',
  '[role="complementary"]',
  '[role="search"]',
  '[role="dialog"]',
  '[aria-hidden="true"]',
  '[hidden]',
  '.nav',
  '.navbar',
  '.navigation',
  '.menu',
  '.site-header',
  '.site-footer',
  '.header',
  '.footer',
  '.sidebar',
  '.side-bar',
  '.breadcrumb',
  '.breadcrumbs',
  '.ad',
  '.ads',
  '.advert',
  '.advertisement',
  '.advertising',
  '.sponsored',
  '.promo-banner',
  '.cookie',
  '.cookies',
  '.cookie-banner',
  '.cookie-notice',
  '.cookie-consent',
  '#cookie-banner',
  '#onetrust-consent-sdk',
  '.social',
  '.social-share',
  '.share-buttons',
  '.newsletter',
  '.subscribe',
  '.related',
  '.related-posts',
  '.comments',
  '.comment-list',
  '.widget',
  '.pagination',
  '.skip-link',
  '.back-to-top',
  '.sr-only',
  '.visually-hidden',
  '.print-only',
  '.screen-reader-text',
];

const BLOCK_TAGS = new Set([
  'ADDRESS', 'ARTICLE', 'ASIDE', 'BLOCKQUOTE', 'DD', 'DIV', 'DL', 'DT', 'FIELDSET', 'FIGCAPTION',
  'FIGURE', 'FOOTER', 'FORM', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'HEADER', 'HR', 'LI', 'MAIN',
  'NAV', 'OL', 'P', 'PRE', 'SECTION', 'TABLE', 'TBODY', 'TD', 'TFOOT', 'TH', 'THEAD', 'TR', 'UL',
]);

/**
 * Collapses whitespace and stray control characters while keeping paragraph
 * breaks. Pure function so it can be unit tested without a DOM.
 */
export function cleanExtractedText(raw: string): string {
  return raw
    .replace(/\r\n?/g, '\n')
    .replace(/\u00a0/g, ' ')
    // A zero-width space is a word separator; joiners and bidi marks are not.
    .replace(/[\u200b\u202f]/g, ' ')
    .replace(/\u{200C}/gu, '')
    .replace(/\u{200D}/gu, '')
    .replace(/\u{200E}/gu, '')
    .replace(/\u{200F}/gu, '')
    .replace(/\u2028/g, '\n')
    .replace(/\u2029/g, '\n')
    .replace(/[^\S\n]+/g, ' ')
    .replace(/ *\n */g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .split('\n')
    .map((line) => line.trim())
    .join('\n')
    .trim();
}

/** Caps text at a hard limit and reports whether anything was dropped. */
export function truncateText(text: string, maxLength: number): { text: string; truncated: boolean } {
  if (text.length <= maxLength) return { text, truncated: false };
  const clipped = text.slice(0, maxLength);
  const lastBreak = clipped.lastIndexOf('\n');
  const safe = lastBreak > maxLength * 0.6 ? clipped.slice(0, lastBreak) : clipped;
  return { text: safe.trimEnd(), truncated: true };
}

/** Chooses between the user's selection and the page body. */
export function pickExtractionSource(
  selectionText: string,
  pageText: string,
): { text: string; source: 'selection' | 'page' } {
  const selection = selectionText.trim();
  if (selection.length >= MIN_SELECTION_LENGTH) {
    return { text: selection, source: 'selection' };
  }
  return { text: pageText, source: 'page' };
}

function collectText(node: Node, out: string[]): void {
  if (node.nodeType === 3 /* TEXT_NODE */) {
    out.push(node.nodeValue ?? '');
    return;
  }
  if (node.nodeType !== 1 /* ELEMENT_NODE */) return;

  const element = node as Element;
  const tag = element.tagName.toUpperCase();
  if (tag === 'BR') {
    out.push('\n');
    return;
  }

  const isBlock = BLOCK_TAGS.has(tag);
  if (isBlock) out.push('\n');
  for (const child of Array.from(element.childNodes)) {
    collectText(child, out);
  }
  if (isBlock) out.push('\n');
}

function textOf(root: Node): string {
  const parts: string[] = [];
  collectText(root, parts);
  return cleanExtractedText(parts.join(''));
}

function removeNoise(root: Element): void {
  for (const selector of NOISE_SELECTORS) {
    let matches: NodeListOf<Element>;
    try {
      matches = root.querySelectorAll(selector);
    } catch {
      continue;
    }
    for (const node of Array.from(matches)) {
      node.remove();
    }
  }
}

function findMainContainer(root: Element): Element | null {
  for (const selector of MAIN_CONTENT_SELECTORS) {
    let match: Element | null = null;
    try {
      match = root.querySelector(selector);
    } catch {
      match = null;
    }
    if (match) return match;
  }
  return null;
}

/**
 * Extracts the readable text of a document.
 * `doc` and `win` are injectable so the behaviour can be exercised in tests.
 */
export function extractReadableContent(
  doc: Document = document,
  win: Window = window,
  maxLength: number = 50_000,
): ExtractedContent {
  const selectionText = (() => {
    try {
      return win.getSelection?.()?.toString() ?? '';
    } catch {
      return '';
    }
  })();

  let pageText = '';
  try {
    const source = doc.body ?? doc.documentElement;
    if (source) {
      const clone = source.cloneNode(true) as Element;
      removeNoise(clone);
      const main = findMainContainer(clone);
      pageText = textOf(main ?? clone);
    }
  } catch {
    pageText = '';
  }

  const picked = pickExtractionSource(selectionText, pageText);
  const capped = truncateText(picked.text, maxLength);

  let title = '';
  let url = '';
  try {
    title = doc.title ?? '';
    url = win.location?.href ?? '';
  } catch {
    title = '';
    url = '';
  }

  return {
    text: capped.text,
    source: picked.source,
    title,
    url,
    charCount: capped.text.length,
    truncated: capped.truncated,
  };
}
