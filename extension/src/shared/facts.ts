/**
 * Turns the backend's structured extraction and the simplification fact list
 * into a compact set of display items for the "Instant Summary" card.
 *
 * Everything rendered here comes from an actual backend response - no value is
 * ever invented to fill a gap in the UI. Items that are not trustworthy
 * (page markers, fragments, headings) are dropped rather than shown.
 */
import type { InstantSummaryItem, PreservedFact, StructuredInformation } from '../types/api';

export type FactKind =
  | 'deadline'
  | 'date'
  | 'document'
  | 'money'
  | 'percentage'
  | 'age'
  | 'condition'
  | 'contact'
  | 'procedure'
  | 'eligibility'
  | 'other';

export type FactSeverity = 'info' | 'warning' | 'critical';

export interface FactItem {
  id: string;
  kind: FactKind;
  label: string;
  value: string;
  text: string;
  severity: FactSeverity;
}

const PRESERVED_FACT_LABELS: Record<string, { label: string; kind: FactKind }> = {
  deadline: { label: 'Deadline', kind: 'deadline' },
  money: { label: 'Amount', kind: 'money' },
  percentage: { label: 'Percentage', kind: 'percentage' },
  age: { label: 'Age requirement', kind: 'age' },
  quantity: { label: 'Quantity', kind: 'other' },
  requirement: { label: 'Requirement', kind: 'eligibility' },
  contact: { label: 'Contact', kind: 'contact' },
  other: { label: 'Key point', kind: 'other' },
};

/** Maximum number of document names shown in one bullet. */
export const MAX_DOCUMENT_NAMES = 5;

/** Maximum number of summary bullets rendered in the popup card. */
export const MAX_SUMMARY_FACTS = 12;

/** "Page 5 of 7" and friends are pagination, never a fact. */
const PAGE_MARKER_PATTERN = /^\s*pages?\s+\d+(\s*(of|out\s+of)\s*\d+)?\s*\.?$/i;

/** A heading such as "PROCEDURE FOR AVAILING THE SCHOLARSHIP" is not a fact. */
const ALL_CAPS_HEADING_PATTERN = /^[A-Z][A-Z ,.'()/&-]*$/;

/**
 * True when the value cannot be shown as a trustworthy fact.
 *
 * Document names are checked separately, because a short name such as "PAN"
 * is a perfectly good fact.
 */
export function isUnusableValue(value: string): boolean {
  const trimmed = value.trim();
  if (trimmed.length < 4) return true;
  if (PAGE_MARKER_PATTERN.test(trimmed)) return true;
  // A value made only of punctuation carries no information.
  if (!/[a-z0-9]/i.test(trimmed)) return true;
  return false;
}

function isHeading(value: string): boolean {
  const trimmed = value.trim();
  if (trimmed.length < 5) return false;
  // A heading is written in capitals, has no digits and has more than one word.
  if (/[0-9]/.test(trimmed)) return false;
  if (!ALL_CAPS_HEADING_PATTERN.test(trimmed)) return false;
  return trimmed.includes(' ');
}

function normaliseForComparison(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9\s₹%]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * True when the candidate says the same thing as something already shown.
 *
 * The same statement often appears twice: once as a procedure step and once as
 * an eligibility rule. Showing it twice makes the summary look repetitive and
 * wastes the limited space in the popup.
 */
export function isDuplicateOf(candidate: string, existing: string[]): boolean {
  const normalised = normaliseForComparison(candidate);
  if (!normalised) return false;

  return existing.some((other) => {
    const otherNormalised = normaliseForComparison(other);
    if (!otherNormalised) return false;
    if (normalised === otherNormalised) return true;
    // Only compare full sentences, never short labels such as "Aadhaar".
    if (normalised.length < 20 || otherNormalised.length < 20) return false;
    return normalised.includes(otherNormalised) || otherNormalised.includes(normalised);
  });
}

function pushItem(items: FactItem[], item: FactItem): void {
  const trimmed = item.value.trim();
  // A pagination marker is never a fact, whatever the category is.
  if (PAGE_MARKER_PATTERN.test(trimmed)) return;
  // A document name can be short ("PAN"); anything else needs some substance.
  if (item.kind !== 'document' && trimmed.length < 4) return;
  if (!/[a-z0-9]/i.test(trimmed)) return;
  if (isHeading(trimmed)) return;
  if (isDuplicateOf(item.value, items.map((existing) => existing.value))) return;
  items.push(item);
}

function formatDocumentNames(names: string[]): string {
  if (names.length <= MAX_DOCUMENT_NAMES) return names.join(', ');
  const shown = names.slice(0, MAX_DOCUMENT_NAMES).join(', ');
  return `${shown} and ${names.length - MAX_DOCUMENT_NAMES} more`;
}

/** Facts derived from `POST /api/documents/extract-info`. */
export function factsFromStructured(info: StructuredInformation | undefined): FactItem[] {
  const items: FactItem[] = [];
  if (!info) return items;

  for (const [index, deadline] of (info.deadlines ?? []).entries()) {
    pushItem(items, {
      id: `deadline-${index}`,
      kind: 'deadline',
      label: deadline.description?.trim() || 'Deadline',
      value: deadline.date,
      text: deadline.original_text || deadline.date,
      severity: 'critical',
    });
  }

  for (const [index, date] of (info.important_dates ?? []).entries()) {
    pushItem(items, {
      id: `date-${index}`,
      kind: 'date',
      label: date.description?.trim() || 'Important date',
      value: date.date,
      text: date.original_text || date.date,
      severity: 'info',
    });
  }

  const documents = (info.required_documents ?? []).map((doc) => doc.name).filter(Boolean);
  if (documents.length) {
    pushItem(items, {
      id: 'documents',
      kind: 'document',
      label: 'Documents needed',
      value: formatDocumentNames(documents),
      text: documents.join(', '),
      severity: 'info',
    });
  }

  for (const [index, amount] of (info.financial_information ?? []).entries()) {
    pushItem(items, {
      id: `money-${index}`,
      kind: 'money',
      label: amount.purpose?.trim() || 'Amount',
      value: amount.amount,
      text: amount.original_text || amount.amount,
      severity: 'info',
    });
  }

  for (const [index, percentage] of (info.percentages ?? []).entries()) {
    pushItem(items, {
      id: `percentage-${index}`,
      kind: 'percentage',
      label: percentage.purpose?.trim() || 'Percentage',
      value: percentage.percentage,
      text: percentage.original_text || percentage.percentage,
      severity: 'info',
    });
  }

  for (const [index, age] of (info.age_requirements ?? []).entries()) {
    const range =
      age.minimum_age !== null && age.minimum_age !== undefined
        ? age.maximum_age !== null && age.maximum_age !== undefined
          ? `${age.minimum_age}–${age.maximum_age} years`
          : `${age.minimum_age}+ years`
        : '';
    if (!range) continue;
    pushItem(items, {
      id: `age-${index}`,
      kind: 'age',
      label: 'Age requirement',
      value: range,
      text: age.original_text || range,
      severity: 'info',
    });
  }

  for (const [index, condition] of (info.important_conditions ?? []).entries()) {
    const type = (condition.type ?? '').toLowerCase();
    pushItem(items, {
      id: `condition-${index}`,
      kind: 'condition',
      label: type === 'exception' ? 'Exception' : type === 'warning' ? 'Warning' : 'Condition',
      value: condition.condition,
      text: condition.original_text || condition.condition,
      severity: type === 'warning' ? 'warning' : 'info',
    });
  }

  for (const [index, contact] of (info.contact_information ?? []).entries()) {
    pushItem(items, {
      id: `contact-${index}`,
      kind: 'contact',
      label: contact.type,
      value: contact.value,
      text: contact.original_text || contact.value,
      severity: 'info',
    });
  }

  for (const [index, procedure] of (info.application_procedure ?? []).entries()) {
    pushItem(items, {
      id: `procedure-${index}`,
      kind: 'procedure',
      label: procedure.step_number ? `Step ${procedure.step_number}` : 'Procedure',
      value: procedure.description,
      text: procedure.original_text || procedure.description,
      severity: 'info',
    });
  }

  for (const [index, requirement] of (info.eligibility_requirements ?? []).entries()) {
    pushItem(items, {
      id: `eligibility-${index}`,
      kind: 'eligibility',
      label: requirement.category?.trim() || 'Eligibility',
      value: requirement.requirement,
      text: requirement.original_text || requirement.requirement,
      severity: 'info',
    });
  }

  return items;
}

/** Facts reported by the simplification endpoint's fact-preservation check. */
export function factsFromPreserved(preserved: PreservedFact[] | undefined): FactItem[] {
  const items: FactItem[] = [];
  for (const [index, fact] of (preserved ?? []).entries()) {
    const mapping = PRESERVED_FACT_LABELS[fact.fact_type] ?? PRESERVED_FACT_LABELS.other;
    pushItem(items, {
      id: `preserved-${index}`,
      kind: mapping.kind,
      label: mapping.label,
      value: fact.value,
      text: fact.source_text || fact.value,
      severity: fact.preserved_in_simplified ? 'info' : 'warning',
    });
  }
  return items;
}

/**
 * Converts a summary item built by the backend into the shape the popup
 * renders. The backend owns the content, so both interfaces show the same
 * facts and the same labels.
 */
export function toFactItem(item: InstantSummaryItem): FactItem {
  return {
    id: item.id,
    kind: item.kind as FactKind,
    label: item.label,
    value: item.value,
    text: item.value,
    severity: item.severity as FactSeverity,
  };
}

export interface FactSummary {
  /** The bullets to render, already capped. */
  facts: FactItem[];
  /** How many trustworthy facts were found before the cap. */
  total: number;
  /** How many facts did not fit into the card. */
  hidden: number;
}

/**
 * Builds the summary bullets.
 *
 * The structured extraction is authoritative for the kinds it covers, so a
 * preserved fact of an already covered kind is dropped instead of being shown
 * twice. Items that repeat an earlier statement are dropped as well.
 */
export function buildFactSummary(
  info: StructuredInformation | undefined,
  preserved: PreservedFact[] | undefined,
  limit: number = MAX_SUMMARY_FACTS,
): FactSummary {
  const merged = factsFromStructured(info);
  const coveredKinds = new Set(merged.map((item) => item.kind));

  for (const fact of factsFromPreserved(preserved)) {
    if (fact.kind !== 'other' && coveredKinds.has(fact.kind)) continue;
    merged.push(fact);
  }

  const total = merged.length;
  return {
    facts: merged.slice(0, limit),
    total,
    hidden: Math.max(0, total - limit),
  };
}

/**
 * Backwards compatible helper that returns only the bullets.
 */
export function buildFactList(
  info: StructuredInformation | undefined,
  preserved: PreservedFact[] | undefined,
  limit: number = MAX_SUMMARY_FACTS,
): FactItem[] {
  return buildFactSummary(info, preserved, limit).facts;
}
