import { useMemo, type ReactNode } from 'react';
import { parseInline, parseMarkdown, type BlockNode, type InlineNode } from '@saral-ui/markdown';

type SimplifiedMarkdownProps = {
  text: string;
  className?: string;
};

function renderInline(nodes: InlineNode[], keyPrefix: string): ReactNode[] {
  return nodes.map((node, index) => {
    const key = `${keyPrefix}-${index}`;
    switch (node.kind) {
      case 'bold':
        return <strong key={key} className="font-extrabold text-neutral-900">{node.value}</strong>;
      case 'italic':
        return <em key={key}>{node.value}</em>;
      case 'code':
        return (
          <code key={key} className="rounded bg-neutral-100 px-1 py-0.5 font-mono text-[0.95em]">
            {node.value}
          </code>
        );
      case 'text':
      default:
        return <span key={key}>{node.value}</span>;
    }
  });
}

function renderBlock(block: BlockNode, index: number): ReactNode {
  const key = `block-${index}`;

  switch (block.kind) {
    case 'heading': {
      const level = Math.min(Math.max(block.level, 2), 4);
      const Tag = (level === 2 ? 'h3' : level === 3 ? 'h4' : 'h5') as 'h3' | 'h4' | 'h5';
      return (
        <Tag key={key} className="mt-3 mb-1 text-sm font-extrabold text-neutral-900 first:mt-0">
          {renderInline(parseInline(block.value), key)}
        </Tag>
      );
    }

    case 'list': {
      const ListTag = block.ordered ? 'ol' : 'ul';
      return (
        <ListTag
          key={key}
          className={`my-1.5 flex list-outside flex-col gap-1 pl-5 ${
            block.ordered ? 'list-decimal' : 'list-disc'
          }`}
        >
          {block.items.map((item, itemIndex) => (
            <li key={`${key}-${itemIndex}`}>{renderInline(parseInline(item), `${key}-${itemIndex}`)}</li>
          ))}
        </ListTag>
      );
    }

    case 'code':
      return (
        <pre
          key={key}
          className="my-2 overflow-x-auto rounded-xl bg-neutral-100 p-3 font-mono text-xs leading-relaxed"
        >
          <code>{block.value}</code>
        </pre>
      );

    case 'paragraph':
    default:
      return (
        <p key={key} className="mb-2 last:mb-0">
          {renderInline(parseInline(block.value), key)}
        </p>
      );
  }
}

/**
 * Renders the simplified text.
 *
 * The parser is shared with the Chrome extension, so the same text is read
 * the same way in both interfaces. The model output is parsed into React
 * elements and is never injected as HTML.
 */
export default function SimplifiedMarkdown({ text, className }: SimplifiedMarkdownProps) {
  const blocks = useMemo(() => parseMarkdown(text ?? ''), [text]);

  if (!blocks.length) return null;

  return <div className={className}>{blocks.map((block, index) => renderBlock(block, index))}</div>;
}
