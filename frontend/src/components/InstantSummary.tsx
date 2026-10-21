import type { ReactNode } from 'react';
import type { InstantSummaryItem } from '../services/api';

type InstantSummaryProps = {
  items: InstantSummaryItem[];
  /** How many further facts were found but did not fit into the summary. */
  hidden?: number;
};

const ICONS: Record<string, ReactNode> = {
  deadline: (
    <svg className="w-4 h-4 text-red-700" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </svg>
  ),
  date: (
    <svg className="w-4 h-4 text-neutral-800" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M8 3v4M16 3v4M3 11h18" />
    </svg>
  ),
  document: (
    <svg className="w-4 h-4 text-neutral-800" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
      <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z" />
    </svg>
  ),
  money: (
    <svg className="w-4 h-4 text-neutral-800" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
      <path d="M7 4h10M7 9h10M15.5 4c0 3.5-2.5 5-6 5h-2l8 11" />
    </svg>
  ),
  percentage: (
    <svg className="w-4 h-4 text-neutral-800" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
      <path d="M19 5 5 19" />
      <circle cx="7" cy="7" r="2.4" />
      <circle cx="17" cy="17" r="2.4" />
    </svg>
  ),
  age: (
    <svg className="w-4 h-4 text-neutral-800" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21v-1a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v1" />
    </svg>
  ),
  condition: (
    <svg className="w-4 h-4 text-amber-700" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
      <path d="M10.3 3.9 2 18a2 2 0 0 0 1.7 3h16.6A2 2 0 0 0 22 18L13.7 3.9a2 2 0 0 0-3.4 0Z" />
      <path d="M12 9v4M12 17h.01" />
    </svg>
  ),
  eligibility: (
    <svg className="w-4 h-4 text-neutral-800" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="9" />
      <path d="m8 12 3 3 5-6" />
    </svg>
  ),
  procedure: (
    <svg className="w-4 h-4 text-neutral-800" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
      <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" />
    </svg>
  ),
  contact: (
    <svg className="w-4 h-4 text-neutral-800" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5M12 8h.01" />
    </svg>
  ),
};

const FALLBACK_ICON = (
  <svg className="w-4 h-4 text-neutral-800" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
    <circle cx="12" cy="12" r="9" />
    <path d="M12 11v5M12 8h.01" />
  </svg>
);

/**
 * The Instant Summary.
 *
 * The list is built by the backend, so the website and the Chrome extension
 * always show the same facts with the same labels. Nothing is derived here.
 */
export default function InstantSummary({ items, hidden = 0 }: InstantSummaryProps) {
  if (!items || !items.length) {
    return (
      <p className="rounded-xl bg-white stroke-border-thin p-3 text-xs font-medium leading-relaxed text-neutral-700">
        No structured facts could be read with confidence from this document. The simplified text
        below is the complete result.
      </p>
    );
  }

  return (
    <>
      <ul className="flex flex-col gap-2 rounded-xl bg-white stroke-border-thin p-3">
        {items.map((item) => (
          <li key={item.id} className="flex items-start gap-2">
            <span className="mt-0.5 shrink-0" aria-hidden="true">
              {ICONS[item.kind] ?? FALLBACK_ICON}
            </span>
            <p className="text-xs font-medium leading-relaxed text-neutral-800">
              <span className="font-extrabold text-neutral-900">{item.label}:</span>{' '}
              {item.value}
            </p>
          </li>
        ))}
      </ul>
      {hidden > 0 ? (
        <p className="mt-1 text-[11px] font-semibold text-neutral-600">
          +{hidden} more fact{hidden === 1 ? '' : 's'} found in the document. The full detail is in
          the simplified document below.
        </p>
      ) : null}
    </>
  );
}
