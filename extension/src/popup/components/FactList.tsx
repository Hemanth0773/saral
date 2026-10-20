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
};

export default function FactList({ facts }: FactListProps) {
  if (!facts.length) return null;

  return (
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
              <span className="sr-only">{fact.label}: </span>
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
  );
}
