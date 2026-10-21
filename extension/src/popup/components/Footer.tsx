import { ExternalLinkIcon } from './Icons';

type FooterProps = {
  onOpenHelp: () => void;
};

export default function Footer({ onOpenHelp }: FooterProps) {
  return (
    <footer className="flex items-center justify-between gap-2 px-1 py-1 text-[10px] font-semibold text-saral-ink/60">
      <div className="flex items-center gap-1">
        <kbd className="rounded border border-saral-ink/30 bg-white px-1.5 py-0.5 font-extrabold text-saral-ink shadow-[1px_1px_0_0_#0D0D0D]">
          Alt+S
        </kbd>
        <span>opens Saral on any page</span>
      </div>
      <button
        type="button"
        onClick={onOpenHelp}
        title="Open the Saral help and documentation"
        className="focus-ring inline-flex items-center gap-1 font-extrabold text-saral-ink underline decoration-saral-ink/40 decoration-2 underline-offset-2 transition-[text-decoration-color] duration-150 hover:decoration-saral-ink"
      >
        <span>Help &amp; Docs</span>
        <ExternalLinkIcon className="text-[12px]" />
      </button>
    </footer>
  );
}
