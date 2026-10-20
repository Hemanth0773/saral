/**
 * A small, safe Markdown subset for the Saral popup.
 *
 * The simplified text comes from a language model, so it can contain
 * Markdown ("**Documents needed**", "- upload the certificate") and, when a
 * model escapes its own output, artefacts such as `\*\*` or `&#x20;`.
 *
 * The text is parsed into a node tree and rendered as React elements. The
 * model output is never injected as HTML, so nothing it contains can turn
 * into markup.
 */

export type InlineNode =
  | { kind: 'text'; value: string }
  | { kind: 'bold'; value: string }
  | { kind: 'italic'; value: string }
  | { kind: 'code'; value: string };

export type BlockNode =
  | { kind: 'paragraph'; value: string }
  | { kind: 'heading'; level: number; value: string }
  | { kind: 'list'; ordered: boolean; items: string[] }
  | { kind: 'code'; value: string };

/** Markdown punctuation the model sometimes escapes. */
const ESCAPED_MARKDOWN = /\\([*_`#>+\-[\]()!|~])/g;

const HTML_ENTITY = /&(#x[0-9a-f]+|#\d+|[a-z][a-z0-9]*);/gi;

const NAMED_ENTITIES: Record<string, string> = {
  amp: '&',
  lt: '<',
  gt: '>',
  quot: '"',
  apos: "'",
  nbsp: ' ',
  ensp: ' ',
  emsp: ' ',
  thinsp: ' ',
  hellip: '…',
  mdash: '—',
  ndash: '–',
  lsquo: '‘',
  rsquo: '’',
  ldquo: '“',
  rdquo: '”',
  bull: '•',
  middot: '·',
  copy: '©',
  reg: '®',
  deg: '°',
  rupee: '₹',
};

function decodeEntity(entity: string, original: string): string {
  const lower = entity.toLowerCase();

  let codePoint: number | null = null;
  if (lower.startsWith('#x')) {
    codePoint = Number.parseInt(lower.slice(2), 16);
  } else if (lower.startsWith('#')) {
    codePoint = Number.parseInt(lower.slice(1), 10);
  }

  if (codePoint !== null) {
    if (!Number.isFinite(codePoint) || codePoint < 0 || codePoint > 0x10ffff) return original;
    // Surrogate halves are not valid characters.
    if (codePoint >= 0xd800 && codePoint <= 0xdfff) return original;
    try {
      return String.fromCodePoint(codePoint);
    } catch {
      return original;
    }
  }

  return NAMED_ENTITIES[lower] ?? original;
}

/**
 * Removes the encoding artefacts a model can leave behind and decodes HTML
 * entities, so the text reads the way it was meant to.
 */
export function normaliseMarkdown(text: string): string {
  if (!text) return '';

  let normalised = text.replace(/\r\n?/g, '\n');

  // Undo the escaping the model applied to Markdown punctuation.
  normalised = normalised.replace(ESCAPED_MARKDOWN, '$1');

  // Decode numeric and common named entities.
  normalised = normalised.replace(HTML_ENTITY, (match, entity: string) =>
    decodeEntity(entity, match),
  );

  return normalised;
}

const INLINE_PATTERN =
  /(\*\*|__)(?=\S)(.+?)(?<=\S)\1|(\*|_)(?=\S)(.+?)(?<=\S)\3|`([^`]+)`/;

/**
 * Splits a line of text into plain and emphasised parts.
 */
export function parseInline(text: string): InlineNode[] {
  const nodes: InlineNode[] = [];
  let rest = text;
  let guard = 0;

  while (rest && guard < 500) {
    guard += 1;
    const match = INLINE_PATTERN.exec(rest);
    if (!match) {
      if (rest) nodes.push({ kind: 'text', value: rest });
      break;
    }

    if (match.index > 0) {
      nodes.push({ kind: 'text', value: rest.slice(0, match.index) });
    }

    if (match[1]) nodes.push({ kind: 'bold', value: match[2] });
    else if (match[3]) nodes.push({ kind: 'italic', value: match[4] });
    else nodes.push({ kind: 'code', value: match[5] ?? '' });

    rest = rest.slice(match.index + match[0].length);
  }

  return nodes;
}

const HEADING_PATTERN = /^(#{1,6})\s+(.*)$/;
const BULLET_PATTERN = /^[-*+]\s+(.*)$/;
const ORDERED_PATTERN = /^(\d+)[.)]\s+(.*)$/;

/**
 * Splits text into blocks: paragraphs, headings, lists and code blocks.
 */
export function parseMarkdown(text: string): BlockNode[] {
  const lines = normaliseMarkdown(text).split('\n');
  const blocks: BlockNode[] = [];

  let paragraph: string[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;
  let code: string[] | null = null;

  const flushParagraph = () => {
    if (paragraph.length) {
      const value = paragraph.join(' ').trim();
      if (value) blocks.push({ kind: 'paragraph', value });
      paragraph = [];
    }
  };

  const flushList = () => {
    if (list) {
      if (list.items.length) blocks.push({ kind: 'list', ordered: list.ordered, items: list.items });
      list = null;
    }
  };

  const flushCode = () => {
    if (code) {
      blocks.push({ kind: 'code', value: code.join('\n') });
      code = null;
    }
  };

  for (const line of lines) {
    const trimmed = line.trim();

    if (code !== null) {
      if (trimmed.startsWith('```')) flushCode();
      else code.push(line);
      continue;
    }

    if (trimmed.startsWith('```')) {
      flushParagraph();
      flushList();
      code = [];
      continue;
    }

    if (!trimmed) {
      flushParagraph();
      flushList();
      continue;
    }

    const heading = HEADING_PATTERN.exec(trimmed);
    if (heading) {
      flushParagraph();
      flushList();
      blocks.push({
        kind: 'heading',
        level: heading[1].length,
        value: heading[2].trim(),
      });
      continue;
    }

    const bullet = BULLET_PATTERN.exec(trimmed);
    if (bullet) {
      flushParagraph();
      if (!list || list.ordered) {
        flushList();
        list = { ordered: false, items: [] };
      }
      list.items.push(bullet[1].trim());
      continue;
    }

    const ordered = ORDERED_PATTERN.exec(trimmed);
    if (ordered) {
      flushParagraph();
      if (!list || !list.ordered) {
        flushList();
        list = { ordered: true, items: [] };
      }
      list.items.push(ordered[2].trim());
      continue;
    }

    // A wrapped continuation of the previous list item.
    if (list && /^\s{2,}\S/.test(line)) {
      list.items[list.items.length - 1] = `${list.items[list.items.length - 1]} ${trimmed}`;
      continue;
    }

    flushList();
    paragraph.push(trimmed);
  }

  flushParagraph();
  flushList();
  flushCode();

  return blocks;
}

/**
 * True when the text contains Markdown that is worth rendering.
 */
export function hasMarkdown(text: string): boolean {
  return parseMarkdown(text).some(
    (block) =>
      block.kind === 'heading' ||
      block.kind === 'list' ||
      block.kind === 'code' ||
      (block.kind === 'paragraph' && /\S(\*\*|__|\*|_|`)/.test(block.value)),
  );
}
