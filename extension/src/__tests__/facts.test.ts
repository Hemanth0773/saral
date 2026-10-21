import test from 'node:test';
import assert from 'node:assert/strict';

import { buildFactList, buildFactSummary, factsFromPreserved, factsFromStructured, MAX_SUMMARY_FACTS } from '../shared/facts.ts';
import type { StructuredInformation } from '../types/api.ts';

const emptyInfo: StructuredInformation = {
  title: null,
  summary: null,
  deadlines: [],
  important_dates: [],
  eligibility_requirements: [],
  age_requirements: [],
  required_documents: [],
  financial_information: [],
  percentages: [],
  application_procedure: [],
  important_conditions: [],
  contact_information: [],
  locations: [],
  organizations: [],
};

test('structured deadlines become critical fact items', () => {
  const facts = factsFromStructured({
    ...emptyInfo,
    deadlines: [
      { date: '2026-12-31', description: 'Application deadline', original_text: 'submit before 31 December 2026' },
    ],
  });

  assert.equal(facts.length, 1);
  assert.equal(facts[0].kind, 'deadline');
  assert.equal(facts[0].value, '2026-12-31');
  assert.equal(facts[0].severity, 'critical');
});

test('required documents are merged into a single fact', () => {
  const facts = factsFromStructured({
    ...emptyInfo,
    required_documents: [
      { name: 'Aadhaar', description: null, original_text: 'Aadhaar' },
      { name: 'Income certificate', description: null, original_text: 'income certificate' },
    ],
  });

  assert.equal(facts.length, 1);
  assert.equal(facts[0].kind, 'document');
  assert.equal(facts[0].value, 'Aadhaar, Income certificate');
});

test('age ranges are rendered with both bounds', () => {
  const facts = factsFromStructured({
    ...emptyInfo,
    age_requirements: [{ minimum_age: 18, maximum_age: 60, original_text: '18 to 60 years old' }],
  });

  assert.equal(facts[0].value, '18–60 years');
});

test('a minimum age without a maximum is rendered with a plus sign', () => {
  const facts = factsFromStructured({
    ...emptyInfo,
    age_requirements: [{ minimum_age: 18, maximum_age: null, original_text: 'at least 18 years old' }],
  });

  assert.equal(facts[0].value, '18+ years');
});

test('warning conditions are marked with a warning severity', () => {
  const facts = factsFromStructured({
    ...emptyInfo,
    important_conditions: [
      { condition: 'Portal locks after the deadline', type: 'warning', original_text: 'locks' },
    ],
  });

  assert.equal(facts[0].severity, 'warning');
  assert.equal(facts[0].label, 'Warning');
});

test('preserved facts are mapped to readable labels', () => {
  const facts = factsFromPreserved([
    { fact_type: 'deadline', value: '31 December 2026', source_text: 'submit before', preserved_in_simplified: true },
    { fact_type: 'money', value: '₹2,50,000', source_text: 'assistance amount', preserved_in_simplified: true },
  ]);

  assert.deepEqual(
    facts.map((fact) => fact.label),
    ['Deadline', 'Amount'],
  );
});

test('a fact that was not preserved is flagged as a warning', () => {
  const facts = factsFromPreserved([
    { fact_type: 'age', value: '18 years', source_text: 'age', preserved_in_simplified: false },
  ]);

  assert.equal(facts[0].severity, 'warning');
});

test('structured facts are preferred and duplicates are removed', () => {
  const merged = buildFactList(
    {
      ...emptyInfo,
      deadlines: [
        { date: '2026-12-31', description: null, original_text: 'submit before 31 December 2026' },
      ],
    },
    [
      { fact_type: 'deadline', value: '31 December 2026', source_text: 'submit before', preserved_in_simplified: true },
      { fact_type: 'money', value: '₹2,50,000', source_text: 'assistance amount', preserved_in_simplified: true },
    ],
  );

  assert.equal(merged.length, 2);
  assert.equal(merged[0].kind, 'deadline');
  assert.equal(merged[1].kind, 'money');
});

test('the fact list is capped so the popup stays compact', () => {
  const preserved = Array.from({ length: 30 }, (_, index) => ({
    fact_type: 'other',
    value: `value-${index}`,
    source_text: `source-${index}`,
    preserved_in_simplified: true,
  }));

  const summary = buildFactSummary(undefined, preserved);

  assert.equal(summary.facts.length, MAX_SUMMARY_FACTS);
  assert.equal(summary.total, 30);
  assert.equal(summary.hidden, 30 - MAX_SUMMARY_FACTS);
});

test('no backend data means no facts are invented', () => {
  assert.deepEqual(buildFactList(undefined, undefined), []);
});
