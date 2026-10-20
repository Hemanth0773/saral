import type { ComponentType, SVGProps } from 'react';
import type { FactItem, FactKind } from '../../shared/facts';
import {
  CalendarIcon,
  CheckCircleIcon,
  DeadlineIcon,
  FolderIcon,
  InfoIcon,
  ListIcon,
  PercentIcon,
  PersonIcon,
  RupeeIcon,
  WarningIcon,
} from './Icons';

type IconComponent = ComponentType<SVGProps<SVGSVGElement>>;

const ICONS: Record<FactKind, IconComponent> = {
  deadline: DeadlineIcon,
  date: CalendarIcon,
  document: FolderIcon,
  money: RupeeIcon,
  percentage: PercentIcon,
  age: PersonIcon,
  condition: WarningIcon,
  contact: InfoIcon,
  procedure: ListIcon,
  eligibility: CheckCircleIcon,
  other: InfoIcon,
};

const SEVERITY_CLASS: Record<FactItem['severity'], string> = {
  info: 'text-saral-ink',
  warning: 'text-amber-700',
  critical: 'text-red-700',
};

type FactListProps = {
  facts: FactItem[];
  /** Number of trustworthy facts that did not fit into the card. */
  hidden?: number;
};

export default function FactList({ facts, hidden = 0 }: FactListProps) {
  if (!facts.length) {
    return (
      <p className="rounded-lg bg-saral-lavender p-2.5 text-[11px] font-medium leading-snug text-saral-ink/70">
        No structured facts could be read with confidence from this document. The simplified
        text above is the complete result.
      </p>
    );
  }

  return (
    <>
      <ul className="flex flex-col gap-2 rounded-lg bg-saral-lavender p-2.5">
        {facts.map((fact) => {
          const Icon = ICONS[fact.kind] ?? InfoIcon;
          return (
            <li key={fact.id} className="flex items-start gap-2">
              <Icon
                className={`mt-0.5 shrink-0 text-[17px] ${SEVERITY_CLASS[fact.severity]}`}
                aria-hidden="true"
              />
              <p className="text-[12px] font-medium leading-snug text-saral-ink">
                <strong className="font-extrabold">{fact.label}:</strong>{' '}
                {fact.value}
                {fact.severity !== 'info' ? (
                  <span className="sr-only">
                    {fact.severity === 'critical' ? ' (important deadline)' : ' (needs attention)'}
                  </span>
                ) : null}
              </p>
            </li>
          );
        })}
      </ul>
      {hidden > 0 ? (
        <p className="text-[10px] font-semibold text-saral-ink/55">
          +{hidden} more fact{hidden === 1 ? '' : 's'} found in the document. The full detail is in
          the simplified text below.
        </p>
      ) : null}
    </>
  );
}
