/**
 * Turns the backend's structured extraction and the simplification fact list
 * into a compact set of display items for the "Instant Summary" card.
 *
 * Everything rendered here comes from an actual backend response — no value is
 * ever invented to fill a gap in the UI.
 */
import type { PreservedFact, StructuredInformation } from '../types/api';

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

function pushItem(items: FactItem[], item: FactItem): void {
  if (!item.value && !item.text) return;
  const duplicate = items.some(
    (existing) =>
      existing.kind === item.kind &&
      existing.value.toLowerCase() === item.value.toLowerCase() &&
      existing.text.toLowerCase() === item.text.toLowerCase(),
  );
  if (!duplicate) items.push(item);
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
      value: documents.join(', '),
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
 * Merges both sources, preferring the structured extraction.
 *
 * The structured extraction is authoritative for the kinds it covers, so a
 * preserved fact of an already covered kind is dropped instead of being shown
 * twice (the two sources spell the same fact differently, e.g. `2026-12-31`
 * versus `31 December 2026`).
 */
export function buildFactList(
  info: StructuredInformation | undefined,
  preserved: PreservedFact[] | undefined,
  limit = 8,
): FactItem[] {
  const merged = factsFromStructured(info);
  const coveredKinds = new Set(merged.map((item) => item.kind));
  const seen = new Set(merged.map((item) => `${item.kind}:${item.value.toLowerCase()}`));

  for (const fact of factsFromPreserved(preserved)) {
    if (fact.kind !== 'other' && coveredKinds.has(fact.kind)) continue;

    const key = `${fact.kind}:${fact.value.toLowerCase()}`;
    if (seen.has(key)) continue;
    seen.add(key);
    merged.push(fact);
  }

  return merged.slice(0, limit);
}
