/**
 * End-to-end check: the real backend response for the scholarship notice,
 * run through the real extension fact derivation and Markdown parser.
 */
import { toFactItem } from '../src/shared/facts.ts';
import { normaliseMarkdown, parseMarkdown } from '../../shared/saral-ui/markdown.ts';

const BASE = process.env.SARAL_BASE_URL ?? 'http://127.0.0.1:8000';

const NOTICE = `3. PROCEDURE FOR AVAILING THE SCHOLARSHIP

I. Students are required to apply annually through the National e-Scholarship Portal. The portal shall remain open for applications as notified by the Commission each year.

II. Incomplete applications will be rejected. The applicant must complete every mandatory field before the final submission, otherwise the form will not be accepted by the portal.

III. The students shall submit the required documents to their institutions to enable, match of name of student, bank account number, and the institution shall upload the same on the portal on behalf of the student.

IV. The bank account of the student must be KYC-compliant. The account must be in the name of the student and must be linked with Aadhaar for the direct benefit transfer.

V. The applicant must provide correct bank details. Any wrong information furnished by the applicant, as per requirement of scheme, will be the sole responsibility of the student.

VI. The institution shall verify the information submitted by the student before uploading the same on the portal.

VII. The institution shall retain the documents for verification for a period of five years from the date of upload. The institution shall produce the documents on demand as and when required by the Commission.

VIII. The University Grants Commission may ask for the documents from the institution for verification at any time and the institution shall comply with such a request without delay.

IX. The student shall upload scanned copies of the certificates along with the application. The documents must be legible and in the prescribed format.

Page 5 of 7
`;

async function post(path, body) {
  const response = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(`${path} -> ${response.status} ${JSON.stringify(payload).slice(0, 300)}`);
  }
  return payload.data ?? payload;
}

const simplification = await post('/api/documents/simplify', {
  text: NOTICE,
  target_grade_level: 5,
});
// The backend builds the canonical summary, so the website and the extension
// render exactly the same facts.
const summary = (simplification.instant_summary ?? []).map(toFactItem);

console.log('=== INSTANT SUMMARY BULLETS (as the popup renders them) ===');
for (const fact of summary) {
  console.log(`  ${fact.label}: ${fact.value}`);
}
console.log(
  `  (${simplification.metadata?.summary_total ?? summary.length} facts found, ` +
    `${simplification.metadata?.summary_hidden ?? 0} hidden)`,
);

console.log('\n=== MALFORMED PATTERN CHECK ===');
const rendered = summary.map((fact) => `${fact.label}: ${fact.value}`).join('\n');
const checks = {
  'duplicated label (Label:Label:)': /(\w[\w ]*):\1:/i.test(rendered),
  'page marker as a fact': /page\s+\d+/i.test(rendered),
  'heading as a fact': /PROCEDURE FOR AVAILING/.test(rendered),
  'fragment starting with punctuation': /^[^:]*: [,;]/m.test(rendered),
  'age direction lost (30+ instead of under 30)': /\b30\+ years/.test(rendered),
};
for (const [name, failed] of Object.entries(checks)) {
  console.log(`  ${failed ? 'PROBLEM' : 'ok'}: ${name}`);
}

console.log('\n=== SIMPLIFIED TEXT (Markdown) ===');
console.log(simplification.simplified_text.slice(0, 600));
console.log('\n=== PARSED BLOCKS ===');
for (const block of parseMarkdown(simplification.simplified_text)) {
  console.log(`  ${block.kind}: ${JSON.stringify(block).slice(0, 140)}`);
}

console.log('\n=== ESCAPE ARTEFACT CHECK ===');
const normalised = normaliseMarkdown(simplification.simplified_text);
for (const token of ['\\*\\*', '\\-', '&#x20;', '&amp;', '\\_']) {
  console.log(`  ${JSON.stringify(token)} -> ${normalised.split(token).length - 1}`);
}
console.log('  literal ** count ->', (normalised.match(/\*\*/g) ?? []).length);
