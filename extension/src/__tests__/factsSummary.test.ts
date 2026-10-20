import test from 'node:test';
import assert from 'node:assert/strict';

import {
  buildFactList,
  buildFactSummary,
  isDuplicateOf,
  isUnusableValue,
  MAX_DOCUMENT_NAMES,
  MAX_SUMMARY_FACTS,
} from '../shared/facts.ts';
import type { StructuredInformation } from '../types/api.ts';

/**
 * The structured information the backend returns for the reported
 * "PROCEDURE FOR AVAILING THE SCHOLARSHIP" notice.
 */
const SCHOLARSHIP_INFO: StructuredInformation = {
  title: null,
  summary: null,
  deadlines: [],
  important_dates: [],
  eligibility_requirements: [
    {
      requirement:
        'The applicant must complete every mandatory field before the final submission, otherwise the form will not be accepted by the portal.',
      category: null,
      original_text:
        'The applicant must complete every mandatory field before the final submission, otherwise the form will not be accepted by the portal.',
    },
    {
      requirement: 'The bank account of the student must be KYC-compliant.',
      category: null,
      original_text: 'The bank account of the student must be KYC-compliant.',
    },
  ],
  age_requirements: [],
  required_documents: [
    { name: 'bank account number', description: null, original_text: 'bank account number' },
    { name: 'correct bank details', description: null, original_text: 'correct bank details' },
    { name: 'Aadhaar', description: null, original_text: 'Aadhaar' },
  ],
  financial_information: [],
  percentages: [],
  application_procedure: [
    {
      step_number: 1,
      description:
        'Students are required to apply annually through the National e-Scholarship Portal.',
      original_text: 'Students are required to apply annually through the National e-Scholarship Portal.',
    },
    {
      step_number: 2,
      description: 'Incomplete applications will be rejected.',
      original_text: 'Incomplete applications will be rejected.',
    },
    {
      step_number: 3,
      description:
        'The institution shall verify the information submitted by the student before uploading the same on the portal.',
      original_text:
        'The institution shall verify the information submitted by the student before uploading the same on the portal.',
    },
    {
      step_number: 4,
      description:
        'The institution shall retain the documents for verification for a period of five years from the date of upload.',
      original_text:
        'The institution shall retain the documents for verification for a period of five years from the date of upload.',
    },
    {
      step_number: 5,
      description:
        'The student shall upload scanned copies of the certificates along with the application.',
      original_text:
        'The student shall upload scanned copies of the certificates along with the application.',
    },
  ],
  important_conditions: [],
  contact_information: [],
  locations: [],
  organizations: [],
};

// ============================================================
// Unusable values
// ============================================================

test('a page marker is not a usable fact', () => {
  assert.equal(isUnusableValue('Page 5 of 7'), true);
  assert.equal(isUnusableValue('Page 12'), true);
  assert.equal(isUnusableValue('page 3 of 10'), true);
});

test('a fragment is not a usable fact', () => {
  assert.equal(isUnusableValue('KYC'), true);
  assert.equal(isUnusableValue('  '), true);
  assert.equal(isUnusableValue('...'), true);
});

test('a real fact is usable', () => {
  assert.equal(isUnusableValue('31 December 2026'), false);
  assert.equal(isUnusableValue('₹2,50,000'), false);
  assert.equal(isUnusableValue('Aadhaar'), false);
});

// ============================================================
// Duplicate labels and repeated statements
// ============================================================

test('a fact value never repeats its own label', () => {
  const facts = buildFactList(SCHOLARSHIP_INFO, undefined);

  for (const fact of facts) {
    const normalisedValue = fact.value.trim().toLowerCase();
    const normalisedLabel = fact.label.trim().toLowerCase();
    assert.equal(
      normalisedValue.startsWith(`${normalisedLabel}:`),
      false,
      `"${fact.label}" must not be repeated inside its own value`,
    );
  }
});

test('the same statement is only shown once', () => {
  assert.equal(isDuplicateOf('The applicant must provide correct bank details.', ['The applicant must provide correct bank details.']), true);
  assert.equal(
    isDuplicateOf(
      'The institution shall retain the documents for verification for a period of five years.',
      ['The institution shall retain the documents for verification for a period of five years from the date of upload.'],
    ),
    true,
  );
  // Short labels are not treated as duplicates of a longer sentence.
  assert.equal(isDuplicateOf('Aadhaar', ['The applicant must submit the Aadhaar card.']), false);
  // Different statements are kept.
  assert.equal(isDuplicateOf('The applicant must provide correct bank details.', ['Incomplete applications will be rejected.']), false);
});

test('a statement repeated as a step and as a rule is only shown once', () => {
  const info: StructuredInformation = {
    ...SCHOLARSHIP_INFO,
    eligibility_requirements: [
      {
        requirement: 'Incomplete applications will be rejected.',
        category: null,
        original_text: 'Incomplete applications will be rejected.',
      },
    ],
  };

  const facts = buildFactList(info, undefined);
  const matching = facts.filter((fact) => fact.value === 'Incomplete applications will be rejected.');

  assert.equal(matching.length, 1);
});

// ============================================================
// Headings and page markers
// ============================================================

test('a section heading is not turned into a fact', () => {
  const info: StructuredInformation = {
    ...SCHOLARSHIP_INFO,
    application_procedure: [
      {
        step_number: 1,
        description: 'PROCEDURE FOR AVAILING THE SCHOLARSHIP',
        original_text: 'PROCEDURE FOR AVAILING THE SCHOLARSHIP',
      },
    ],
  };

  const facts = buildFactList(info, undefined);

  assert.equal(
    facts.some((fact) => fact.value.includes('PROCEDURE FOR AVAILING')),
    false,
  );
});

test('a page marker is not turned into a fact', () => {
  const info: StructuredInformation = {
    ...SCHOLARSHIP_INFO,
    application_procedure: [
      { step_number: 1, description: 'Page 5 of 7', original_text: 'Page 5 of 7' },
    ],
    eligibility_requirements: [
      { requirement: 'Page 5 of 7', category: null, original_text: 'Page 5 of 7' },
    ],
  };

  const facts = buildFactList(info, undefined);

  assert.equal(
    facts.some((fact) => /page\s+\d+/i.test(fact.value)),
    false,
  );
});

// ============================================================
// The reported scholarship notice
// ============================================================

test('the scholarship notice produces useful summary bullets', () => {
  const facts = buildFactList(SCHOLARSHIP_INFO, undefined);
  const text = facts.map((fact) => `${fact.label}: ${fact.value}`).join('\n');

  // The document names are a clean list, not a run-on of sentence fragments.
  const documents = facts.find((fact) => fact.kind === 'document');
  assert.ok(documents, 'the documents bullet is missing');
  assert.equal(documents.label, 'Documents needed');
  assert.ok(documents.value.includes('Aadhaar'));
  assert.equal(
    documents.value.includes('to their institutions to enable'),
    false,
    'a sentence fragment must not be presented as a document name',
  );

  // Every important topic of the notice is represented.
  assert.ok(text.includes('annually through the National e-Scholarship Portal'));
  assert.ok(text.includes('Incomplete applications will be rejected'));
  assert.ok(text.includes('KYC-compliant'));
  assert.ok(text.includes('verify the information'));
  assert.ok(text.includes('retain the documents'));
  assert.ok(text.includes('upload scanned copies of the certificates'));

  // Nothing malformed.
  assert.equal(text.includes('Eligibility:Eligibility:'), false);
  assert.equal(text.includes('Documents needed:Documents needed:'), false);
  assert.equal(text.includes('Step 1:Step 1:'), false);
});

test('every bullet is a complete statement or a short label', () => {
  const facts = buildFactList(SCHOLARSHIP_INFO, undefined);

  for (const fact of facts) {
    if (fact.kind === 'document') continue;
    assert.ok(
      fact.value.length >= 15,
      `"${fact.value}" is too short to be a useful fact`,
    );
    assert.equal(/^\s*[,:;]/.test(fact.value), false, `"${fact.value}" starts with punctuation`);
  }
});

test('the summary stays within the popup budget', () => {
  const summary = buildFactSummary(SCHOLARSHIP_INFO, undefined);

  assert.ok(summary.facts.length <= MAX_SUMMARY_FACTS);
  assert.equal(summary.total, summary.facts.length + summary.hidden);
});

test('a long list of document names is shortened', () => {
  const names = Array.from({ length: 9 }, (_, index) => `document number ${index}`);
  const info: StructuredInformation = {
    ...SCHOLARSHIP_INFO,
    required_documents: names.map((name) => ({ name, description: null, original_text: name })),
  };

  const documents = buildFactList(info, undefined).find((fact) => fact.kind === 'document');

  assert.ok(documents);
  assert.ok(documents.value.includes('more'));
  assert.equal(documents.value.split(',').length <= MAX_DOCUMENT_NAMES + 1, true);
});

// ============================================================
// Ordinary responses still work
// ============================================================

test('a plain response without structure produces no facts', () => {
  const summary = buildFactSummary(undefined, undefined);
  assert.deepEqual(summary.facts, []);
  assert.equal(summary.total, 0);
});

test('a simple deadline is still reported', () => {
  const info: StructuredInformation = {
    ...SCHOLARSHIP_INFO,
    deadlines: [
      {
        date: '2026-12-31',
        description: 'Application deadline',
        original_text: 'submit before 31 December 2026',
      },
    ],
  };

  const facts = buildFactList(info, undefined);
  const deadline = facts.find((fact) => fact.kind === 'deadline');

  assert.ok(deadline);
  assert.equal(deadline.value, '2026-12-31');
  assert.equal(deadline.severity, 'critical');
});

test('a preserved fact is still reported when nothing else exists', () => {
  const facts = buildFactList(undefined, [
    {
      fact_type: 'money',
      value: '₹2,50,000',
      source_text: 'The assistance amount is ₹2,50,000',
      preserved_in_simplified: true,
    },
  ]);

  assert.equal(facts.length, 1);
  assert.equal(facts[0].label, 'Amount');
  assert.equal(facts[0].value, '₹2,50,000');
});
