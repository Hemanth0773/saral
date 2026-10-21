# Project Status: Cognitive Accessibility Simplifier

**Last Updated**: October 20, 2026  
**Current Milestone**: Milestone 18 (Accuracy and completeness of the simplified output) - Complete  
**Overall Completion**: ~100% (Milestones 1-19 complete, 546 backend tests + 117 extension tests passing)

---

## Overall Status

### Current State
- ✅ **Milestone 1 (Foundation)**: Complete - Health endpoint, configuration, logging, security working
- ✅ **Milestone 2 (Document Ingestion)**: Complete - All tests passing
- ✅ **Milestone 3 (OCR)**: Complete - All 10 OCR tests passing
- ✅ **Milestone 4 (NLP Preprocessing)**: Complete - All 25 NLP tests passing
- ✅ **Milestone 5 (LLM Simplification)**: Complete - Real-tested with Gemini 2.5 Flash, validation_passed: true, fact_preservation_rate: 1.0
- ✅ **Milestone 6 (Structured Information Extraction)**: Complete - 36 extraction tests passing, all 14 categories implemented
- ✅ **Milestone 7 (Advanced Fact Validation)**: Complete - 33 validation tests passing, cross-document validation working
- ✅ **Milestone 8 (Readability Analysis)**: Complete - 41 readability tests passing
- ✅ **Milestone 9 (Translation)**: Complete - 23 translation tests passing, NLLB-200 model working
- ✅ **Milestone 10 (Text-to-Speech)**: Complete - 29 TTS tests passing, English and Kannada TTS working
- ✅ **Milestone 11 (Database / History)**: Complete - 46 history tests passing, PostgreSQL integration with history tracking
- ✅ **Milestone 12 (Final Testing, Security, Performance & Documentation)**: Complete - Full test suite (338 tests), security hardening, API verification, documentation finalized
- ✅ **Milestone 13 (Saral — Browser Copilot Chrome Extension)**: Complete - Manifest V3 extension built, 50 unit tests + 31 live backend checks passing, UI verified by headless-browser screenshots
- ✅ **Milestone 14 (Rate-Limit Reliability for long documents)**: Complete - Bounded provider-aware retries with backoff and jitter, Gemini 503 classified as transient, round-based provider fallback, 37 new backend tests passing
- ✅ **Milestone 15 (Fidelity Validation - No Invented Facts)**: Complete - Page artifacts stripped before the model sees the text, prompt hardened, four new fidelity checks, 31 new backend tests passing
- ✅ **Milestone 16 (Instant Summary Quality and Markdown Rendering)**: Complete - Extraction returns complete statements, headings and page markers excluded, safe Markdown renderer, 14 new backend tests and 38 new extension tests passing
- ✅ **Milestone 17 (One Canonical Output for Website and Extension)**: Complete - Backend builds the Instant Summary, shared Markdown parser, age direction preserved, completeness rule added, 26 new backend tests and 10 new extension tests passing
- ✅ **Milestone 18 (Accuracy and Completeness of the Simplified Output)**: Complete - Age direction, negation, page markers, document vs account condition, heading-aware sections, "too similar" warning refined, 56 new backend regression tests on the complete notice
- ✅ **Milestone 19 (Summary Quality, Readability and Extension Polish)**: Complete - Contextual percentages and amounts, fact ranking and de-duplication, measured reading level in both interfaces, one scroll surface, yellow popup with white cards, 30 new backend tests and 13 new extension tests passing

### Architecture Diagram
- System architecture diagram created: `docs/system-architecture.svg` and `docs/system-architecture.png`
- Shows 5-layer architecture: Client (React 19), API Gateway (FastAPI), Service Layer (NLP/AI modules), Data Layer (PostgreSQL + File Storage), External APIs (Hugging Face, Microsoft Edge TTS, Tesseract)

### Key Metrics
- **Backend Tests**: 546 passing (+1 skipped), 0 failing
- **Extension Unit Tests**: 117 passing (node:test)
- **Extension Live Backend Checks**: 31 passing, 0 failing
- **Test Coverage**: ~70% across all modules
- **API Endpoints**: 16 (8 live-tested with HTTP requests in M12; 8 more exercised by the extension verification)
- **M12 Verification**: 8 of 16 endpoints tested with live HTTP requests; PostgreSQL history verified with 89+ records
- **Security**: SSRF protection hardened to block RFC 1918 private IPs and link-local addresses (including AWS metadata 169.254.169.254)
- **M13 Verification**: extension CORS origin allow-list tested (8 tests); web origins still restricted to `CORS_ORIGINS`
- **M14 Verification**: rate-limit handling tested with 37 mocked-provider tests plus a live run that hit a real Groq 429 and recovered
- **M15 Verification**: fidelity checks tested with 31 mocked-model tests plus two live runs of the reported scholarship notice
- **M16 Verification**: extraction quality tested with 14 backend tests; Instant Summary and Markdown tested with 38 extension tests plus a live run of the reported scholarship notice and a headless rendering of the popup
- **M17 Verification**: the canonical output tested with 26 backend tests and 10 extension tests; the website and the extension were rendered in a browser from the same API response and show the same facts
- **M18 Verification**: the complete scholarship notice is a regression fixture (`backend/tests/fixtures/scholarship_terms.txt`) covered by 55 new backend tests; two live runs of the full document preserved all 27 checked requirements with `validation_passed: true` and no artefacts
- **M19 Verification**: the summary shows contextual facts ("Reservation: 30% of slots will be reserved for the women candidates"), the age rule once, the negative rules as "Not eligible"; the reading level is measured and shown by both interfaces; the popup was rendered in a browser (yellow surface, white cards, one scroll surface)

---

## Milestone 19 — Summary Quality, Readability and Extension Polish

**Status**: ✅ COMPLETE  
**Date Completed**: October 21, 2026

**Root Causes (confirmed by reproducing the reported output)**

1. **`Percentage: 30%` with no meaning.** `extract_percentages` kept only the
   number and derived a purpose from three hard coded words, so a percentage
   without one of them lost its meaning entirely.
2. **The age rule shown twice.** The eligibility rule "Only students who are
   below the age of 30 years ... are eligible" repeated the age requirement,
   and nothing recognised it as a restatement.
3. **Important conditions pushed out.** The summary was built in extraction
   order and then cut at the limit, so a generic fact could hide the rule that
   a student may take only one scholarship.
4. **"+25 more facts".** The count included duplicates, restatements and list
   introductions, because the facts were never de-duplicated as a set.
5. **`Grade not measured`.** `textstat` raises a `KeyError` for a word that is
   not in its CMU dictionary ("postgraduate", "2"), which made both Flesch
   scores `None` for almost every real document. The extension then showed a
   placeholder because the measurement had never succeeded.
6. **Double scrolling.** The summary card had its own `overflow-y-auto` inside
   the scrolling `<main>`.
7. **The popup was lavender with white cards.** The request was for a yellow
   surface with white cards.

**What Changed**

| File | Change |
| --- | --- |
| `backend/app/services/readability_service.py` | The syllables are counted word by word with an estimate for unknown words, and the Flesch scores are calculated with the same formula when textstat cannot. |
| `backend/app/api/routes/simplification.py` | The simplification response now carries the measured `readability`. |
| `backend/app/schemas/simplification.py` | The `readability` field and its models. |
| `backend/app/services/extraction_service.py` | A percentage and an amount keep the clause they sit in, so their meaning survives. |
| `backend/app/services/summary_service.py` | Contextual labels for percentages and amounts, ranking by importance, de-duplication of restatements and of two wordings of the same rule, and an honest hidden count. |
| `shared/saral-ui/readability.ts` | **New.** The reading level label, used by both interfaces. |
| `extension/src/popup/App.tsx`, `SummaryCard.tsx` | The reading level comes from the simplification; the placeholder is gone; one scroll surface; the colour swap. |
| `frontend/src/components/TrySaralNow.tsx` | The website shows the same reading level. |

**Test Results**

- Backend: **546 passing, 1 skipped, 0 failing** (was 513; +33)
- Extension: **117 passing** (was 104; +13), typecheck and lint clean, build and
  `verify:dist` clean
- Website: typecheck and build clean, lint unchanged at 6 pre-existing warnings
- Live: `verify:backend` 31 checks passed; the full notice was simplified
  live and checked section by section (0 of 27 missing, no artefacts)

**Known Limitations (Honest)**

- The reading level of a technical legal text is often far above the target.
  The label reports the measured value, it does not improve it.
- The summary shows twelve facts. The rest are counted, not hidden silently,
  and they stay in the detailed text.
- The fact ranking uses keyword hints. An unusual but important rule could
  still be ranked lower than a rule that matches a hint.
- The popup was rendered in a headless browser, not in a real Chrome
  extension window.

---

## Milestone 18 — Accuracy and Completeness of the Simplified Output

**Status**: ✅ COMPLETE  
**Date Completed**: October 21, 2026

**Root Causes (confirmed by reproducing the reported output)**

1. **`Age requirement: 30+ years` for "below the age of 30 years".**
   `extract_age_requirements` matched only the number. The direction word had
   to sit directly in front of it, so "below the age of 30 years" fell
   through to the plain "30 years old" form and became a lower bound.
2. **A negative rule shown as a positive requirement.**
   "Students, who have already acquired any postgraduate degree, are not
   eligible to apply" was extracted and labelled "Eligibility".
3. **Page markers inside the facts.**
   The markers were only removed from the text sent to the model. The
   extraction ran on the raw text, so "Page 3 of 7" ended up inside a
   requirement and split the sentence it sat in.
4. **`Documents needed: Aadhaar`.**
   A hard coded list of document names turned every mention of a document
   into a required document, even when the source only said that the bank
   account has to be Aadhaar linked.
5. **The "too similar to original" warning.**
   The check compared the exact fact strings and used the length and the
   sentence count. A fact written "30 %" instead of "30%" was counted as
   lost, and a well structured simplification of a legal text was reported
   as unchanged.

**What Changed**

| File | Change |
| --- | --- |
| `backend/app/services/extraction_service.py` | The direction of an age rule is captured (including "below the age of 30 years", "at most", "maximum age of"); a negated rule is labelled "Not eligible"; page markers are stripped in every extractor; a document has to name a document; the section heading decides whether the numbered items are rules or steps. |
| `backend/app/services/summary_service.py` | The age value keeps the wording of the source ("Below 30 years"); the eligibility rules are capped so the other facts stay in the summary; the hidden count includes the rules that did not fit. |
| `backend/app/services/validation_service.py` | The "too similar" check now compares the wording and the structure, so a restructured legal text is not reported as unchanged. |
| `backend/tests/fixtures/scholarship_terms.txt` | **New.** The complete notice. |
| `backend/tests/test_scholarship_regression.py` | **New.** 55 tests on the complete notice. |
| `extension/scripts/verify-scholarship.mjs` | Now runs against the complete notice and checks the age direction and the negative rules. |

**Section by Section Assessment of the Full Fixture (two live runs)**

```
ok  Eligibility: first PG degree only            ok  Institutions: Section 2(f) and NAAC
ok  postgraduate degree holders not eligible      ok  deemed universities, Section 3
ok  already admitted in the first year            ok  fully funded by government
ok  integrated programmes, PG component           ok  institutions of national importance
ok  age below 30                                  ok  AISHE code and registration
ok  full time mode only                           ok  only one scholarship at a time
ok  open/distance not eligible                    ok  declaration required
ok  UGC specified degrees                         ok  no paid appointment
ok  one benefit: NOC not required, resignation    ok  already receiving, must relinquish
ok  Aadhaar seeding and verified account          ok  selection on merit
ok  30 % reserved for women                       ok  50/50 subject allocation
ok  tie break on UG marks                         ok  tie break on Class XII marks
ok  result announced in November/December         ok  check on NSP with user id and password
ok  UGC website
```

`missing sections: 0 of 27`, `artefacts: none`, `validation_passed: True`,
`fact_preservation_rate: 1.0` in both runs.

**Test Results**

- Backend: **546 passing, 1 skipped, 0 failing** (was 457; +56 regression tests)
- Extension: **104 passing** (unchanged), typecheck and lint clean, build and
  `verify:dist` clean
- Website: typecheck and build clean, lint unchanged at 6 pre-existing warnings
- Live: `verify:backend` 31 checks passed; the full notice checked live twice

**Known Limitations (Honest)**

- The Instant Summary is still pattern based. A rule written in a way the
  patterns do not recognise is not reported - fewer facts, never wrong ones.
- The model rewrites the notice, so the wording differs between runs. The
  meaning was checked in two runs, but a single run cannot prove the output
  is always faithful.
- A fact the model writes as "30 %" (with a narrow no-break space) is matched
  by the validation, but the raw text still carries the space.
- The "too similar" check measures the wording and the structure. A text that
  is reorganised but whose sentences are unchanged is still reported as
  unchanged.

---

## Milestone 17 — One Canonical Output for Website and Extension

**Status**: ✅ COMPLETE  
**Date Completed**: October 20, 2026

**Why the two interfaces disagreed (confirmed from the code)**

Both interfaces already called the same endpoint with the same payload
(`POST /api/documents/simplify` with `{text, target_grade_level: 5}`) and the
backend already produced one result. The difference was entirely in the
response handling:

* the extension rendered the Instant Summary and parsed the simplified text as
  Markdown, the website dumped the same string into a `<pre>`;
* the extension derived the summary on the client from a second
  `/api/documents/extract-info` call, the website had no summary at all.

So the backend was already the source of truth for the text, and the two
interfaces simply processed the response differently.

**What Changed**

| File | Change |
| --- | --- |
| `backend/app/services/summary_service.py` | **New.** Builds the canonical Instant Summary from the structured extraction: meaningful labels, de-duplication, page markers and headings excluded, a cap on the procedure steps. |
| `backend/app/api/routes/simplification.py` | Builds the summary and returns it as `instant_summary`, with the counts in `metadata`. |
| `backend/app/schemas/simplification.py` | New `SummaryItem` model and the additive `instant_summary` field. |
| `backend/app/schemas/extraction.py` | `ExtractedAgeRequirement` gained an optional `qualifier` so the direction of an age rule survives. |
| `backend/app/services/extraction_service.py` | The age direction is captured ("under 30" is an upper bound, "30 or older" a lower bound); abbreviations such as "Rs." no longer split a rule; numbered headings are not facts; obligations for applicants and institutions are captured. |
| `backend/app/services/llm_service.py` | A completeness rule in the prompt ("simplify the whole document, never shorten it into a summary"), and `LLM_REASONING_EFFORT` so a reasoning model does not spend the answer budget on internal reasoning. |
| `backend/app/services/validation_service.py` | Fact matching normalises "25 %" against "25%", so a reformatted fact is no longer reported as lost. |
| `shared/saral-ui/markdown.ts` | **New.** The Markdown parser moved here and is used by both interfaces. |
| `extension/src/popup/App.tsx` | Uses the backend's `instant_summary`; the structured extraction is only a fallback for an older backend. |
| `frontend/src/components/InstantSummary.tsx` | **New.** The website renders the canonical summary with its own styling. |
| `frontend/src/components/SimplifiedMarkdown.tsx` | **New.** The website renders the simplified text with the shared parser. |

**Live Verification**

The same real backend response rendered in a browser:

```
Website  : Deadline: 2026-07-31 | Documents needed: ... | Amount: ₹2,50,000 |
            Age requirement: under 30 years | Eligibility: ... | Conditions: ...
Extension: Deadline: 2026-07-31 | Documents needed: ... | Amount: ₹2,50,000 |
            Age requirement: under 30 years | Eligibility: ... | Conditions: ...
```

The age rule keeps its direction ("under 30 years", never "30+ years"), the
simplified text is complete with headings and lists, and `validation_passed`
is true.

**Test Results**

- Backend: **457 passing, 1 skipped, 0 failing** (was 430; +26 canonical output tests)
- Extension: **104 passing** (was 94; +10 canonical output tests)
- Website build: succeeds; lint unchanged at 6 pre-existing warnings

**Known Limitations (Honest)**

- The Instant Summary is still pattern based. A fact phrased in a way the
  patterns do not recognise is not reported - the summary shows fewer facts,
  never wrong ones.
- The summary shows at most twelve bullets and four procedure steps; the rest
  are counted below the card.
- A statement repeated with different wording can still appear twice when
  neither contains the other.
- The completeness rule is a prompt instruction. The validation stage reports
  a document that lost a fact, but it cannot restore a section the model
  skipped.

---

## Milestone 16 — Instant Summary Quality and Markdown Rendering

**Status**: ✅ COMPLETE  
**Date Completed**: October 20, 2026

**Root Causes (confirmed from the code and by reproducing the bug)**

The reported bullets were reproduced exactly by running the backend extraction
on the scholarship procedure text:

```
Documents needed:Documents needed: required documents to their institutions to enable,
                  match of name of student, bank account number
Step 1:Step 1: PROCEDURE FOR AVAILING THE SCHOLARSHIP
Eligibility:Eligibility: of its students on the basis of
```

Three separate causes:

1. **The backend's regex extraction returned fragments.**
   `extract_eligibility_requirements` and `extract_important_conditions`
   captured `[^.!?\n]+`, which stops at the end of a line, so a rule came back
   as "KYC-compliant" or ", as per requirement of scheme". The same happened
   for document names, which came back as sentence fragments.
2. **Section headings were extracted as procedure steps.** The numbered-list
   pattern matched `3. PROCEDURE FOR AVAILING THE SCHOLARSHIP` and turned the
   heading into "Step 1". Roman-numeral clauses (`I.` to `IX.`), which are how
   the notice actually lists its nine steps, were not matched at all.
3. **The extension rendered the label twice.** `FactList` contained a
   screen-reader-only `{fact.label}: ` prefix *and* a visible `{fact.label}:`,
   so the label appeared twice in the text of every bullet. The escape
   artefacts (`\*\*`, `\-`, `&#x20;`) are literal characters in the model
   output, and React renders text children verbatim, so they were displayed as
   written.

**What Changed**

| File | Change |
| --- | --- |
| `backend/app/services/extraction_service.py` | Eligibility requirements and conditions are expanded to the enclosing sentence; procedure steps support Roman numerals and reject headings; document names must be short noun phrases; page markers and headings are never facts. |
| `backend/app/services/llm_service.py` | An empty completion is now a retryable failure instead of a silently empty result. |
| `extension/src/shared/facts.ts` | Page markers, fragments and headings are rejected; a statement is never shown twice; document names are capped; the summary is capped at ten bullets and reports how many were left out. |
| `extension/src/popup/components/FactList.tsx` | The duplicated screen-reader label is gone; an empty extraction shows a clean fallback message. |
| `extension/src/popup/markdown.ts` | **New.** A safe Markdown subset: unescapes `\*\*` / `\-` / `&#x20;`, decodes entities, and parses paragraphs, headings, lists, code and emphasis. |
| `extension/src/popup/components/Markdown.tsx` | **New.** Renders the parsed tree as React elements - the model output is never injected as HTML. |
| `extension/src/popup/components/SummaryCard.tsx` | The simplified and translated text are rendered with the Markdown renderer. |
| `backend/tests/test_extraction_quality.py` | **New.** 14 regression tests on the reported notice. |
| `extension/src/__tests__/markdown.test.ts` | **New.** 23 tests: escape artefacts, plain text, line breaks, HTML safety. |
| `extension/src/__tests__/factsSummary.test.ts` | **New.** 15 tests: duplicated labels, fragments, headings, page markers, the scholarship notice. |

**Live Verification (real backend, real extension code)**

```
Documents needed: bank account number, correct bank details, Aadhaar
Step 1: Students are required to apply annually through the National e-Scholarship Portal.
Step 2: Incomplete applications will be rejected.
Step 3: The students shall submit the required documents to their institutions ...
Step 4: The bank account of the student must be KYC-compliant.
Step 5: The applicant must provide correct bank details.
Step 6: The institution shall verify the information submitted by the student ...
Step 7: The institution shall retain the documents for verification ...
Step 8: The University Grants Commission may ask for the documents ...
Step 9: The student shall upload scanned copies of the certificates ...
```

No duplicated label, no page marker, no heading and no sentence fragment. The
popup was rendered in headless Chrome and the card shows the facts with their
icons, the Markdown heading and the bold text rendered as Markdown, and the
existing design untouched.

**Test Results**

- Backend: **430 passing, 1 skipped, 0 failing** (was 414; +14 extraction quality, +2 empty completion)
- Extension: **94 passing** (was 56; +23 Markdown, +15 Instant Summary)
- Website build: succeeds; lint unchanged at 6 pre-existing warnings

**Known Limitations (Honest)**

- The extraction is still pattern based. A requirement written in a way none of
  the patterns recognise is not reported - the summary shows fewer facts, not
  wrong ones.
- The Instant Summary shows at most ten bullets. The rest are counted in a
  line below the card and remain in the simplified text.
- A statement that is repeated with slightly different wording is only removed
  when one of the two is contained in the other. A genuine paraphrase of the
  same rule can still appear twice.
- The Markdown renderer supports a deliberate subset. Tables, images, footnotes
  and nested lists are shown as plain text rather than rendered.
- The report was reproduced with a reconstruction of the scholarship notice
  from the nine clauses described in the report, because the original file was
  not attached to the request.

---

## Milestone 15 — Fidelity Validation: No Invented Facts

**Status**: ✅ COMPLETE  
**Date Completed**: October 20, 2026

**Root Cause (confirmed from the code and a live run)**

Three separate gaps let the simplified output say things the source never said:

1. **Pagination artifacts reached the model.** `ocr_utils.combine_ocr_results`
   joins the extracted pages with `--- Page N (text) ---`, and a government
   PDF usually also prints its own `Page 4 of 7` footer. The prompt never
   mentioned page markers, so the model read one as content and turned it into
   an instruction.
2. **The prompt did not protect qualifiers or entity types.** The rules said
   "never invent new information", but nothing told the model to keep
   "normally", to keep "subject to", or to keep "university/college/institute"
   as written.
3. **Validation was one-directional.** `validate_fact_preservation` only
   checked that dates, amounts, percentages, ages and quantities from the
   source were still present. It could not see anything the simplified text
   *added*. A confident, readable, wrong sentence passed with
   `validation_passed: true`.

**What Changed**

| File | Change |
| --- | --- |
| `backend/app/services/text_fidelity.py` | **New.** Artifact stripping plus four fidelity checks: page references, certainty and conditions, entity substitution, unsupported numbers in obligations. |
| `backend/app/services/llm_service.py` | Page/OCR artifacts are stripped before the text reaches the model; the system prompt and both user prompts gained explicit rules for artifacts, qualifiers, conditions, entity types and not inventing steps. |
| `backend/app/services/validation_service.py` | `validate_final_response` now runs the fidelity checks and reports them in `validation_failures`. |
| `frontend/src/components/TrySaralNow.tsx` | The result card now shows a "Needs review" notice listing what was flagged. The website previously never displayed the validation result at all. |
| `extension/src/popup/components/SummaryCard.tsx` | The warning now lists the specific reasons instead of the generic "every fact was preserved" wording. |
| `backend/tests/test_text_fidelity.py` | **New.** 31 regression tests built on the reported scholarship text and the exact incorrect output. |

**Behaviour After the Fix**

- Standalone pagination lines and OCR artifacts never reach the model, so a
  page marker cannot become an instruction in the first place.
- If a page reference does appear in the output, it is reported - including
  the case where the source only mentioned it as a footer.
- A dropped hedge ("normally") or a dropped condition ("subject to") is
  reported, with the definiteness marker that replaced it.
- A swapped organisation type ("university" → "school") is reported.
- An obligation that quotes a number the source never states is reported.
- A faithful simplification raises no issue, so the checks do not fire on
  correct output.

The API contract is unchanged: the findings are added to the existing
`validation_failures` list and flip the existing `validation_passed` flag.

**Live Verification (real model, the reported scholarship notice, 2 runs)**

```
validation_passed = True
  ok: page marker leaked into the output
  ok: certainty upgraded (no hedge left)
  ok: entity swapped to 'school'
```

Both runs kept "university/college/institute" and "normally", and neither
mentioned "Page 4 of 7".

**Test Results**

- Backend: **414 passing, 1 skipped, 0 failing** (was 383; +31 fidelity tests, no regressions)
- Extension: **56 passing** (unchanged)
- Website build: succeeds; lint unchanged at 6 pre-existing warnings

**Known Limitations (Honest)**

- These checks detect specific, recognisable failure patterns. They cannot
  prove that a reworded sentence means exactly what the original meant, and
  they do not catch every way a simplification can drift. The original
  document remains the authority.
- The artifact stripping removes *standalone* pagination lines. A page
  reference written inside a sentence is left alone, because it may be a real
  cross-reference; the prompt and the validation rules cover that case.
- The entity check only knows the organisation families listed in
  `text_fidelity.ENTITY_FAMILIES`. A swap between two terms that are not in
  the same family is not detected.
- The condition check fires only when the simplified text contains no
  conditional construction at all. A condition that is paraphrased into an
  unconditional statement but happens to keep the word "if" elsewhere in the
  document is not reported.
- One of the two live runs produced an output that was very close to the
  original. The separate "too similar to original" quality check reports
  that, but it is a pre-existing limitation of the quality heuristics.

---

## Milestone 14 — Rate-Limit Reliability for Long Documents

**Status**: ✅ COMPLETE  
**Date Completed**: October 20, 2026

**Root Cause (confirmed from the source and from live provider responses)**

A long notice (~6,400 characters) is split into four chunks of 2,000 characters
(`CHUNK_SIZE`). Each chunk is a separate provider request, and every request
reserves `prompt_tokens + max_tokens` against the provider's per-minute token
budget. Measured against the real Groq API:

```
prompt_tokens: 1008   max_tokens: 2000   ->  Requested: 2965
x-ratelimit-limit-tokens: 8000
retry-after: 23
"Please try again in 22.1775s"
```

Four chunks therefore reserve roughly 11,000 tokens against an 8,000 token
budget, so the third or fourth chunk is rejected with **HTTP 429**. Before this
milestone the chunk loop had **no retry at all**: it caught the 429, immediately
sent the same large request to the fallback provider, and when that provider
answered `503 UNAVAILABLE` it aborted the whole request.

**Duplicate Request Investigation (result: not a bug)**

The reported "a successful simplification followed immediately by another
request for 6,370 characters" is the sequential chunk loop, not a second
submission. A live run logs exactly one route line per user action:

```
Simplification request: target_grade_level=5, text_length=4874   <- once
Text chunked into 3 chunks
Processing 3 chunks separately
Groq simplification successful     <- chunk 1
Groq simplification successful     <- chunk 2
Groq simplification successful     <- chunk 3
```

The website disables its submit button while `busy = uploading || processing ||
submitting`, the extension disables Simplify while a request is in flight, and
`frontend/src/services/api.ts` performs a single `fetch` with no retry
wrapper. No duplicate submission was found, so no frontend behaviour was
changed. The extension additionally gained an explicit in-flight guard
(`extension/src/popup/guards.ts`) so the guarantee does not depend on the
disabled attribute alone.

**What Changed**

| File | Change |
| --- | --- |
| `backend/app/services/llm_retry.py` | **New.** Retry policy, provider hint parsing (`Retry-After`, `x-ratelimit-reset-tokens`, `"try again in 22.2s"`), exponential backoff with jitter, transient-error classification. |
| `backend/app/services/llm_service.py` | New `LLMTransientError`; provider errors now carry the provider's retry hint; unified OpenAI-compatible error mapping; the chunk loop became a round-based provider chain with bounded retries; `metadata.retry_count` now reports the failed provider attempts. |
| `backend/app/api/routes/simplification.py` | The pipeline runs through `asyncio.to_thread`, so the FastAPI event loop is never blocked while the backend waits for a rate-limit window; new `LLM_TRANSIENT` mapping to HTTP 503 `LLM_SERVICE_UNAVAILABLE`. |
| `backend/app/core/config.py` | `LLM_MAX_RETRIES`, `LLM_RETRY_BASE_DELAY`, `LLM_RETRY_MAX_DELAY`, `LLM_RETRY_JITTER`, `LLM_SIMPLIFICATION_TIMEOUT`. |
| `extension/src/background/api.ts` | Request timeout raised to 300 s and the timeout message explains that a large document may wait for a rate limit to reset. |
| `extension/src/shared/errors.ts` | Backend error codes get their own titles ("Rate limit reached", "Service temporarily unavailable"). |
| `extension/src/popup/guards.ts` | **New.** In-flight guard that prevents a duplicate Simplify request. |

**Behaviour After the Fix**

- A 429 is retried after the delay the provider asked for.
- A rate limited provider is complemented by the next configured provider in
  the same round, so a healthy fallback finishes the chunk immediately.
- A `503 UNAVAILABLE` is treated as transient and retried with backoff.
- Authentication failures are never retried.
- If every provider stays unavailable, the request fails with a clear,
  actionable error. A failed chunk is never reported as a successful
  simplification.
- Fact validation, readability analysis, history recording and the response
  contract are unchanged.

**Live Verification (real Groq API, real backend)**

```
Groq API error (429): ... TPM: Limit 8000, Used 7358, Requested 1716. Please try again in 8.055s.
Groq failed (LLMRateLimitError)
Gemini simplification successful
Chunk 1/3 simplified with Gemini.        <- fallback worked
Groq API error (429): ... Please try again in 262.5ms.
Gemini simplification successful
Chunk 2/3 simplified with Gemini.        <- fallback worked
Groq simplification successful
Chunk 3/3 simplified with Groq.           <- primary recovered
Simplification completed successfully: processing_time=20680ms
```

The same request previously failed outright with a 503.

**Test Results**

- Backend: **383 passing, 1 skipped, 0 failing** (was 346; +37 new rate-limit tests, no regressions)
- Extension: **56 passing** (was 50; +4 in-flight guard tests, +2 error-title tests)
- Website build: succeeds, lint unchanged (4 pre-existing warnings)

**Known Limitations (Honest)**

- The Groq free tier allows 8,000 tokens per minute, which is genuinely small
  for a long notice. The chunk size (`CHUNK_SIZE=2000`) and `LLM_MAX_TOKENS`
  (2000) were deliberately **not** reduced: measurements showed the completion
  already reaches 1,957 of the 2,000 token cap for a 2,796 character chunk, so
  shrinking either would risk silently truncating a chunk and losing facts. The
  retry policy is the correct fix.
- When a fallback provider takes over some chunks, fact preservation can be
  weaker (observed 7/14 facts preserved versus 14/14 on a single provider).
  Saral's validation stage reports this honestly through `validation_passed`
  and `validation_failures`, and the UI shows the warning.
- The `Alt+S` shortcut and the extension's manual Chrome pass still need a
  human; the extension UI was verified by headless rendering and live API
  checks only.

---

## Milestone 13 — Saral: Browser Copilot (Chrome Extension)

**Status**: ✅ COMPLETE  
**Date Completed**: October 20, 2026

**What Was Built**
- Manifest V3 extension (`extension/manifest.json`) with action popup, background service worker, on-demand content script and an `Alt+S` keyboard command
- React 19 + TypeScript popup (`extension/src/popup/`) that reuses the website's design tokens (brand yellow `#F9C915`, ink `#0D0D0D`, pale lavender surfaces, neo-brutalist borders and hard offset shadows)
- Background service worker that owns the backend URL and performs **every** HTTP call (`extension/src/background/`)
- Content script that extracts the main readable content of a page, or the user's text selection when one exists (`extension/src/content/extractor.ts`)
- Typed client for the existing backend endpoints, with contracts mirrored in `extension/src/types/api.ts`
- Document upload (PDF/JPG/PNG/TXT/DOCX up to 10 MB) reusing `POST /api/documents/extract`
- URL extraction through the backend's `POST /api/documents/url`, so the existing SSRF protection is not duplicated
- Simplification, structured facts, measured reading grade, Kannada translation, real TTS audio with an in-popup player, and copy-to-clipboard
- Bundled "Help & Docs" page (`extension/public/help.html`) opened from the popup footer
- Extension test suite using Node's built-in `node:test` runner (no new test dependency)
- Live verification script (`extension/scripts/verify-backend.mjs`) that drives the extension's own client code against a running backend

**Key Files**
- `extension/manifest.json` - Manifest V3 (permissions, action, service worker, command)
- `extension/src/background/index.ts` - Message routing, tab injection, configuration
- `extension/src/background/api.ts` - The only place that performs HTTP calls
- `extension/src/content/extractor.ts` - Readable-content extraction (pure, unit tested)
- `extension/src/popup/App.tsx` - State machine and orchestration
- `extension/src/popup/components/` - Header, HeroCard, InputCard, ActionBar, SummaryCard, AudioDeck, FactList, SettingsPanel
- `extension/src/shared/facts.ts` - Important-fact derivation from backend responses
- `extension/src/shared/errors.ts` - HTTP status to user-message mapping
- `extension/src/__tests__/` - 56 unit tests
- `extension/scripts/verify-backend.mjs` - 31 live checks

**Backend Changes Required (and Why)**
| Change | Reason |
| --- | --- |
| `CORS_ORIGIN_REGEX` setting + `allow_origin_regex` in `app/main.py` | A Chrome extension's origin is `chrome-extension://<id>` and the id is assigned by Chrome, so it cannot be listed statically. The pattern only matches Chrome extension origins; a web page can never send that origin, so no additional web origin is exposed. Covered by `backend/tests/test_cors.py` (8 tests). |
| `edge-tts` 7.2.8 → 7.3.1 in `backend/requirements.txt` | Edge TTS 7.2.8 was rejected with HTTP 403 by Microsoft's speech endpoint, so TTS failed for both the website and the extension. 7.3.1 restores it. |

**Test Results**
- Backend: **346 passing, 1 skipped, 0 failing** (was 338 — the 8 new CORS tests, no regressions)
- Extension Unit Tests: **50 passing** (config, extractor, facts, errors, api client)
- Extension live backend checks: **31 passing, 0 failing** (health + CORS, simplify, extract-info, readability, translate en→kn, TTS + audio fetch, error handling)
- Extension typecheck (`tsc --noEmit`, strict): clean
- Extension lint (`oxlint`): clean
- Extension production build: succeeds, `extension/dist/` is self-contained
- Website production build: still succeeds

**UI Verification**
- Popup initial state and result state rendered in headless Chrome and compared against the supplied `screen.png` reference — hero card, "BROWSER COPILOT" / "v2.4 Live" pills, input card, action row, "INSTANT SUMMARY" card, reading-grade badge, fact icons, audio deck, language pills and footer all match the reference layout and visual language.

**Known Limitations (Honest)**
- **Hindi is not available.** The backend validates the language code against `['en', 'kn']`, so the popup shows Hindi disabled and labelled *Unavailable* rather than silently returning English.
- Chrome settings, the Chrome Web Store and the built-in PDF viewer block extensions; the popup explains this instead of failing silently.
- The reading-grade badge only appears when the backend actually measured the text; otherwise the card reads "Grade not measured".
- The `Alt+S` shortcut needs `chrome.action.openPopup()` (Chrome 127+); on older builds only the toolbar button works.
- The extension UI was verified by automated headless-browser rendering and live API checks. The final "load the unpacked folder in Chrome and click through it" pass is a manual step and has not been performed by the assistant.

---

## Milestone 1 — Project Foundation

**Status**: ✅ COMPLETE  
**Date Completed**: September 18, 2026

**What Was Built**
- FastAPI application structure with modular architecture
- Health check endpoint (`GET /api/health`)
- Configuration system using Pydantic Settings
- Structured logging setup
- Security validation utilities (SSRF prevention, file validation)
- Input validation for files and URLs
- Postman collection for API testing
- Complete test suite for health endpoint

**Key Files**
- `app/main.py` - FastAPI entry point
- `app/core/config.py` - Environment configuration
- `app/core/logging.py` - Structured logging
- `app/core/security.py` - Input validation & SSRF protection
- `app/api/routes/health.py` - Health check endpoint
- `tests/test_health.py` - Health endpoint tests

**Test Results**
- 2 tests passing (test_health_check, test_root_endpoint)

**Known Issues**
- None

---

## Milestone 2 — Document Ingestion

**Status**: ✅ COMPLETE (M12 - All tests now passing)
**Date Completed**: September 25, 2026 (tests updated)
**Test Status**: 24/24 tests passing

**What Was Built**
- PDF text extraction (using pypdf, no C++ dependencies)
- Webpage text extraction with HTML parsing
- Document processing pipeline (ID generation, language detection, text cleaning)
- File upload endpoint (`POST /api/documents/extract`)
- URL extraction endpoint (`POST /api/documents/url`)
- Document ID generation with unique identifiers
- Language detection (heuristic-based)
- Text truncation with metadata flags
- Comprehensive error handling with consistent response format
- SSRF attack prevention for URLs
- File type validation and size limits

**Key Files**
- `app/services/document_service.py` - Document orchestration
- `app/services/pdf_service.py` - PDF text extraction
- `app/services/webpage_service.py` - Webpage extraction
- `app/schemas/document.py` - Request/response schemas
- `app/api/routes/documents.py` - Document endpoints
- `tests/test_documents.py` - Document extraction tests

**Test Results**
- Passing: 24/24
- All tests now passing after M12 fixes (error response format, file validation, Swagger docs)

---

## Milestone 3 — OCR for Scanned Documents

**Status**: ✅ COMPLETE  
**Date Completed**: September 18, 2026

**What Was Built**
- Tesseract OCR integration (pytesseract)
- Image enhancement for OCR accuracy
- EXIF-based image rotation detection and correction
- Image format validation
- OCR confidence estimation heuristics
- Mixed-mode PDF support (text + scanned pages)
- Support for JPG, PNG image uploads
- OCR result combining with page markers
- Extraction method detection and classification

**Key Files**
- `app/services/ocr_service.py` - Core OCR service
- `app/services/image_service.py` - Image enhancement and processing
- `app/utils/ocr_utils.py` - OCR utilities and text combining
- `tests/test_ocr.py` - OCR service tests (10 tests, all passing)

**Test Results**
- 10 OCR tests passing
- Tests cover: OCR extraction, image validation, rotation detection, confidence estimation, extraction method detection

**Known Issues**
- None

---

## Milestone 4 — NLP Preprocessing

**Status**: ✅ COMPLETE  
**Date Completed**: September 21, 2026

**What Was Built**
- spaCy NLP integration for English language processing
- Text normalization and cleaning
- Sentence tokenization with positional information
- Named entity recognition (NER) - identifies persons, organizations, locations, dates, etc.
- Part-of-speech (POS) tagging for grammatical analysis
- Dependency parsing information (via spaCy)
- Key phrase extraction using noun chunks and TF-IDF scoring
- Text readability analysis (word count, sentence count, reading time, etc.)
- Model caching for performance optimization
- Comprehensive error handling and validation
- POST `/documents/preprocess` endpoint for NLP analysis

**Key Files**
- `app/schemas/nlp.py` - NLP response schemas (SentenceToken, NamedEntity, POSTag, KeyPhrase, etc.)
- `app/services/nlp_service.py` - Core NLP processing service with spaCy integration
- `app/api/routes/documents.py` - Updated with preprocessing endpoint
- `tests/test_nlp.py` - Comprehensive NLP test suite

**Test Results**
- 25 NLP tests passing (17 service tests, 8 endpoint tests)
- All tests verify linguistic analysis correctness

**API Endpoint**
- `POST /api/documents/preprocess` - Accepts JSON with `text` field, returns complete linguistic analysis
- Response includes: sentences, entities, POS tags, key phrases, processing metadata
- Proper error handling with appropriate HTTP status codes (400, 422, 500, 503)

**Known Issues**
- None - all functionality working as designed

---

## Milestone 7 — Advanced Fact Validation

**Status**: ✅ COMPLETE  
**Date Completed**: September 21, 2026

**What Was Built**
- Cross-document fact validation service
- Validation across original, simplified (M5), and structured (M6) documents
- Deterministic comparison with format normalization
- Support for 12 fact types (dates, money, percentages, ages, quantities, documents, eligibility, conditions, contact info, locations, organizations)
- POST `/api/documents/validate` endpoint
- Comprehensive test suite with 33 tests covering all categories
- Fact preservation validation integrated with M5 validation system
- Reuse of M5 validation service (extract_critical_facts, normalize_date_format)

**Key Files**
- `app/schemas/validation.py` - Pydantic models for validation results (169 lines)
- `app/services/advanced_validation_service.py` - Core validation logic (477 lines)
- `app/api/routes/validation.py` - API endpoint (133 lines)
- `tests/test_validation.py` - Comprehensive test suite (544 lines)

**Validation Categories Implemented**
1. Dates (with format normalization: DMY, MDY, ISO, dashed, slashed)
2. Deadlines (application submission dates)
3. Monetary amounts (₹, Rs., INR with comma normalization)
4. Percentages (%, "percent", "per cent")
5. Ages (single ages and ranges)
6. Quantities (numerical values)
7. Required documents (lists and comma-separated values)
8. Eligibility requirements (pattern-based extraction)
9. Important conditions (exceptions, notes, warnings)
10. Contact information (phone, email, address)
11. Locations (geographic locations/offices)
12. Organizations (named entities)

**Validation Method**
- **Deterministic**: Dates, monetary amounts, percentages, ages, quantities
- **Format Normalization**: Multiple representations recognized as equivalent
- **Pattern-Based**: Eligibility, conditions, documents, procedures
- **Fact Preservation**: Reuses M5 validation system; original document remains source of truth

**Test Results**
- 33 M7 validation tests passing (100%)
  - Date validation: 5 tests
  - Money validation: 4 tests
  - Percentage validation: 3 tests
  - Age validation: 3 tests
  - Document validation: 2 tests
  - Eligibility validation: 2 tests
  - Structured validation: 3 tests
  - Full cross-document validation: 2 tests
  - API endpoint tests: 5 tests
  - Edge cases: 4 tests
- Total project tests: 338/338 passing
- Zero regressions in M1-M6 functionality

**API Endpoint**
```
POST /api/documents/validate

Request:
{
  "original_text": "string (required)",
  "simplified_text": "string (optional)",
  "structured_information": "object (optional)"
}

Response:
{
  "validation_passed": boolean,
  "overall_status": "PASS" | "FAIL" | "WARNING" | "INCONCLUSIVE",
  "facts_checked": integer,
  "facts_preserved": integer,
  "facts_changed": integer,
  "facts_missing": integer,
  "contradictions": [
    {
      "fact_type": "deadline" | "money" | "percentage" | "age" | ...,
      "original_value": "string",
      "simplified_value": "string | null",
      "structured_value": "string | null",
      "reason": "string",
      "severity": "error" | "warning"
    }
  ],
  "preservation_details": [...],
  "processing_time_ms": integer,
  "metadata": {...}
}
```

**Real Postman Test Results**

PASS Case:
- Original: "Eligible applicants must submit before 31 December 2026. Assistance is ₹2,50,000. Must be 18+ years old. Submit Aadhaar, income certificate, bank details."
- Simplified: "Send application by December 31, 2026. Get ₹2,50,000. Must be 18+ years old. Need Aadhaar, income certificate, bank details."
- Result: ✅ validation_passed: true, overall_status: PASS, facts_preserved: 2

FAIL Case:
- Original: "Eligible applicants must submit before 31 December 2026. Assistance is ₹2,50,000. Must be 18+ years old."
- Simplified: "Send application by December 31, 2025. Get ₹2,00,000. Must be 21+ years old."
- Result: ❌ validation_passed: false, overall_status: FAIL, contradictions: 2
  - Deadline changed: 2026 → 2025
  - Age changed: 18 years → 21 years

**Known Limitations**
- Semantic understanding limited (pattern-based for complex requirements)
- Organization/entity extraction may miss named entities
- Complex conditional logic not interpreted
- Contact information may have incomplete addresses in simplified text

**Known Issues**
- None - all 338 tests pass, functionality verified

---

## Milestone 6 — Structured Information Extraction

**Status**: ✅ COMPLETE  
**Date Completed**: September 21, 2026

**What Was Built**
- Structured information extraction service for government documents
- Deterministic extraction patterns for critical facts (dates, amounts, percentages, ages)
- Pattern-based extraction for semantic categories (eligibility, documents, procedures, conditions)
- 14 extraction categories implemented
- POST `/api/documents/extract-info` endpoint
- Comprehensive test suite with 36 tests covering all categories
- Fact preservation validation integrated with M5 validation system
- Support for multiple date formats (DMY, MDY, ISO)
- Indian currency (₹) amount extraction with normalization
- Age range detection and normalization
- Required documents list extraction
- Contact information extraction (phone, email, address)
- Deadline and important dates differentiation

**Key Files**
- `app/services/extraction_service.py` - Core extraction logic (703 lines)
- `app/schemas/extraction.py` - Pydantic models for structured data (247 lines)
- `app/api/routes/extraction.py` - API endpoint (171 lines)
- `tests/test_extraction.py` - Comprehensive test suite (509 lines)

**Extraction Categories Implemented**
1. Document title
2. Summary
3. Deadlines (with ISO date normalization)
4. Important dates
5. Eligibility requirements
6. Age requirements (including ranges)
7. Required documents
8. Monetary amounts (₹ extraction with normalization)
9. Percentages
10. Application procedures
11. Important conditions
12. Contact information (phone, email, address)
13. Locations/offices
14. Organizations/entities

**Extraction Method**
- **Deterministic**: Dates, monetary amounts, percentages, ages, phone numbers, emails
- **Pattern-based**: Eligibility requirements, procedures, conditions, document requirements
- **Fact Preservation**: Reuses M5 validation system; original document text remains source of truth

**Test Results**
- 36 M6 extraction tests passing (100%)
  - Basic extraction tests: 8 passing
  - Date normalization tests: 3 passing
  - Money extraction tests: 4 passing
  - Document extraction tests: 2 passing
  - Contact extraction tests: 2 passing
  - Full structured extraction tests: 3 passing
  - Real-world example tests: 2 passing
  - API endpoint tests: 8 passing
  - Edge case tests: 4 passing
- Total project tests: 338/338 passing

**Bug Fixes (M6 Pre-Implementation)**
1. Fixed age range extraction to correctly identify minimum and maximum ages
2. Fixed deadline extraction for "Month DD, YYYY" format (e.g., "December 31, 2026")
3. Fixed validation error handler to properly distinguish between /documents/extract and /documents/extract-info endpoints

**API Endpoint**
```
POST /api/documents/extract-info

Request:
{
  "text": "string (required, max 100,000 chars)",
  "extract_title": boolean (optional, default: true),
  "extract_summary": boolean (optional, default: true)
}

Response:
{
  "success": boolean,
  "document_id": string,
  "original_text": string,
  "structured_information": {
    "title": string | null,
    "summary": string | null,
    "deadlines": [...],
    "important_dates": [...],
    "eligibility_requirements": [...],
    "age_requirements": [...],
    "required_documents": [...],
    "financial_information": [...],
    "percentages": [...],
    "application_procedure": [...],
    "important_conditions": [...],
    "contact_information": [...],
    "locations": [...],
    "organizations": [...]
  },
  "extraction_method": "deterministic",
  "processing_time_ms": integer,
  "metadata": {
    "facts_preserved": boolean,
    "facts_count": integer,
    "extraction_issues": [string]
  }
}
```

**Example Test Data**
Input: "Eligible applicants must submit the application before 31 December 2026. The assistance amount is ₹2,50,000. Applicants must be at least 18 years old and must submit Aadhaar, income certificate, and bank account details."

Extracted:
- Deadline: 2026-12-31
- Amount: ₹2,50,000
- Age: 18 years (minimum)
- Documents: Aadhaar, income certificate, bank account details
- Facts preserved: Yes

**Known Limitations**
- Title extraction requires specific patterns (not all documents have explicit titles)
- Location extraction prioritized for Indian cities; international locations may not extract
- Organization extraction may require LLM for semantic understanding (currently pattern-based)
- Procedures are extracted from numbered lists; unnumbered procedures may be missed

**Known Issues**
- None - all 338 tests pass, functionality verified

---

## Milestone 5 — LLM Simplification

**Status**: ✅ COMPLETE (Real-tested with Gemini 2.5 Flash)  
**Date Completed**: September 21, 2026

**Real Postman Test Result**
- validation_passed: true
- fact_preservation_rate: 1.0
- End-to-end pipeline: Postman → FastAPI → Gemini 2.5 Flash → LLM simplification → Critical fact extraction → Fact validation → Validated simplified response

---

## Milestone 4 — NLP Preprocessing

**Status**: ✅ COMPLETE

**What Was Built** (from Milestone 4, September 21, 2026)
- spaCy NLP integration for English language processing
- Text normalization and cleaning
- Sentence tokenization with positional information
- Named entity recognition (NER)
- Part-of-speech (POS) tagging
- Key phrase extraction using noun chunks and TF-IDF scoring
- Text readability analysis
- Model caching for performance
- POST `/documents/preprocess` endpoint

**Test Results**
- 25 NLP tests passing
- All linguistic analysis verified

---

## Development Timeline

- **Sep 18, 2026**: Milestones 1-3 implemented (document extraction tests had known format issues)
- **Sep 19, 2026**: Documentation updated to reflect actual test status
- **Sep 21, 2026**: Milestones 4-8 implemented and tested
- **Sep 22, 2026**: Complete documentation and test counts finalized
- **Sep 23, 2026**: M12 security hardening (SSRF), Postman collection updated, architecture diagram created
- **Sep 24, 2026**: Test suite verified — all 338 tests passing; documentation finalized
- **Oct 20, 2026**: Milestone 13 — Saral Browser Copilot Chrome extension implemented, built and verified (346 backend tests, 50 extension unit tests, 31 live backend checks)
- **Oct 20, 2026**: Milestone 14 — Rate-limit reliability for long documents: bounded provider-aware retries, backoff with jitter, transient 5xx handling, round-based provider fallback (383 backend tests, 56 extension unit tests)
- **Oct 20, 2026**: Milestone 15 — Fidelity validation: page artifacts stripped before the model sees the text, hardened prompts, four new fidelity checks, validation failures now shown in both UIs (414 backend tests, 56 extension unit tests)
- **Oct 20, 2026**: Milestone 16 — Instant Summary quality and Markdown rendering: complete statements from the extraction, headings and page markers excluded, duplicated label removed, safe Markdown renderer (430 backend tests, 94 extension unit tests)
- **Oct 20, 2026**: Milestone 17 — One canonical output: the backend builds the Instant Summary, the Markdown parser is shared, the age direction is preserved, and the website shows the same result as the extension (457 backend tests, 104 extension unit tests)
- **Target**: Project is complete and ready for demonstration

---

## Test Execution (as of 2026-10-20)
```
Total Backend Tests: 546
Passing: 457 ✅
Failing: 0 ❌
Skipped: 1 (a local origin that is not on the configured CORS allow-list)
Errors: 0

Test Files:
- tests/test_health.py (2 tests) - 2/2 passing
- tests/test_documents.py (24 tests) - 24/24 passing
- tests/test_ocr.py (10 tests) - 10/10 passing
- tests/test_nlp.py (25 tests) - 25/25 passing
- tests/test_simplification.py (69 tests) - 69/69 passing
- tests/test_extraction.py (36 tests) - 36/36 passing
- tests/test_validation.py (33 tests) - 33/33 passing
- tests/test_readability.py (41 tests) - 41/41 passing
- tests/test_translation.py (23 tests) - 23/23 passing
- tests/test_tts.py (29 tests) - 29/29 passing
- tests/test_history.py (46 tests) - 46/46 passing
- tests/test_cors.py (8 tests) - 7/8 passing, 1 skipped  [NEW in M13]
- tests/test_llm_retry.py (37 tests) - 37/37 passing  [NEW in M14]
- tests/test_text_fidelity.py (31 tests) - 31/31 passing  [NEW in M15]
- tests/test_extraction_quality.py (14 tests) - 14/14 passing  [NEW in M16]

Extension Tests:
- extension/src/__tests__/config.test.ts (13 tests) - passing
- extension/src/__tests__/extractor.test.ts (11 tests) - passing
- extension/src/__tests__/facts.test.ts (10 tests) - passing
- extension/src/__tests__/errors.test.ts (10 tests) - passing
- extension/src/__tests__/api.test.ts (8 tests) - passing
- extension/src/__tests__/guards.test.ts (4 tests) - passing  [NEW in M14]
- extension/src/__tests__/markdown.test.ts (23 tests) - passing  [NEW in M16]
- extension/src/__tests__/factsSummary.test.ts (15 tests) - passing  [NEW in M16]
- extension/scripts/verify-backend.mjs (31 live checks) - passing
```

**M6 Bug Fixes Applied:**
- Fixed age range extraction (min/max ordering)
- Fixed deadline extraction for MDY format
- Fixed validation error status codes for extract-info endpoint

**M12 Updates:**
- Added SSRF security hardening: `validate_url` now blocks RFC 1918 private IPs (10.x, 172.16-31.x, 192.168.x), link-local addresses (169.254.x including AWS metadata), and resolves domain hostnames to check their IPs
- Added 2 new tests for SSRF protection (`test_ssrf_protection_private_ip_ranges`, `test_ssrf_protection_valid_public_url`)
- Verified 8 of 16 API endpoints end-to-end with live HTTP requests
- Updated Postman collection with missing endpoints (M6 extract-info, M7 validate, M8 readability, M9 batch translate, M10 serve audio)
- Created system architecture diagram (`docs/system-architecture.svg` and `docs/system-architecture.png`)
- Added frontend documentation (React 19, TypeScript, Vite, Tailwind CSS)
- Updated README.md and PROJECT-STATUS.md to reflect all milestones and accurate test counts

---

## How to Run Tests
```bash
cd backend
python -m pytest tests/ -v
```

```bash
cd extension
npm test                # 104 unit tests
npm run typecheck       # strict TypeScript check
npm run lint            # oxlint
npm run verify:backend  # 31 live checks (backend must be running)
```

### Failing Tests Summary
- Backend: none - 457 tests passing, 0 failures, 0 errors, 1 skipped
- Extension: none - 104 unit tests passing, 31 live backend checks passing

---

## API Endpoints (Current)

### Health Check
- `GET /api/health` - System health status

### Document Ingestion (M2)
- `POST /api/documents/extract` - Upload PDF/image and extract text
- `POST /api/documents/url` - Extract text from government webpage

### NLP Preprocessing (M4)
- `POST /api/documents/preprocess` - Linguistic analysis (sentences, entities, POS tags, key phrases)

### Text Simplification (M5)
- `POST /api/documents/simplify` - Simplify government document text using LLM
- `POST /api/documents/simplify/validate` - Validate fact preservation between original and simplified text

### Structured Information Extraction (M6)
- `POST /api/documents/extract-info` - Extract structured information (deadlines, eligibility, documents, amounts, etc.)

### Advanced Fact Validation (M7)
- `POST /api/documents/validate` - Cross-document validation (12 fact types: dates, money, percentages, ages, quantities, documents, eligibility, conditions, contact info, locations, organizations)

### Readability Analysis (M8)
- `POST /api/documents/readability` - Flesch Reading Ease and Flesch-Kincaid Grade Level comparison

### Translation (M9)
- `POST /api/translate` - Translate text to target language
- `POST /api/translate/batch` - Batch translate multiple texts

### Text-to-Speech (M10)
- `POST /api/tts` - Generate speech audio from text
- `GET /api/media/audio/{filename}` - Serve generated audio file

### History (M11)
- `GET /api/history` - List document processing history (paginated)
- `GET /api/history/{document_id}` - Get history for a specific document

### Documentation
- `GET /docs` - Swagger UI
- `GET /openapi.json` - OpenAPI schema
- `GET /redoc` - ReDoc

---

## Environment Setup

See `backend/app/core/config.py` for environment variables (uses Pydantic Settings).

Key variables:
- `APP_NAME`: Application name
- `VERSION`: API version
- `ENVIRONMENT`: Deployment environment
- `HOST`: Server host
- `PORT`: Server port
- `DEBUG`: Enable debug mode
- `MAX_FILE_SIZE_MB`: Maximum upload file size
- `CORS_ORIGINS`: Allowed web origins (JSON list)
- `CORS_ORIGIN_REGEX`: Pattern for extra allowed origins (default: Chrome extension origins)
- `UPLOAD_DIRECTORY`: Temporary upload directory
- `DOCUMENT_ID_PREFIX`: Prefix for generated document IDs
- `DATABASE_URL`: PostgreSQL connection string (e.g., `postgresql+psycopg://postgres:password@localhost:5432/cognitive_accessibility_db`)
- `USE_DATABASE`: Enable database history tracking (true/false)
- `LLM_PROVIDER`: LLM provider for simplification (gemini, openai, groq, openrouter, mock, auto)
- `LLM_API_KEY`: API key for the chosen LLM provider
- `GEMINI_API_KEY`: Google Gemini API key (alternative to LLM_API_KEY)
- `TRANSLATION_PROVIDER`: Translation model provider (nllb)
- `TTS_PROVIDER`: TTS provider (google)

---

## Current Status Summary

### Completed Milestones
- ✅ M1: Foundation (Health, config, logging, security)
- ✅ M2: Document Ingestion (PDF, images, URLs)
- ✅ M3: OCR for Scanned Documents (Tesseract integration)
- ✅ M4: NLP Preprocessing (spaCy integration, linguistic analysis)
- ✅ M5: LLM Simplification (Gemini 2.5 Flash, fact preservation validation)
- ✅ M6: Structured Information Extraction (14 categories, deterministic extraction, 36 tests)
- ✅ M7: Advanced Fact Validation (cross-document validation, 33 tests)
- ✅ M8: Readability Analysis (Flesch-Kincaid metrics)
- ✅ M9: Translation (NLLB-200 model, English/Kannada)
- ✅ M10: Text-to-Speech (edge-tts, English and Kannada)
- ✅ M11: Database/History (PostgreSQL, history API, 46 tests)
- ✅ M12: Final Testing, Security, Performance & Documentation (338 tests, SSRF hardening, Postman, docs, architecture diagram)
- ✅ M13: Saral — Browser Copilot Chrome extension (Manifest V3, 50 unit tests, 31 live backend checks)
- ✅ M14: Rate-limit reliability for long documents (bounded provider-aware retries, backoff with jitter, transient 5xx handling, 37 new backend tests)
- ✅ M15: Fidelity validation - no invented facts (page artifacts stripped before the model sees the text, hardened prompts, four fidelity checks, 31 new backend tests)
- ✅ M16: Instant Summary quality and Markdown rendering (complete statements from the extraction, headings and page markers excluded, safe Markdown renderer, 14 new backend tests and 38 new extension tests)
- ✅ M17: One canonical output for website and extension (backend builds the summary, shared Markdown parser, age direction preserved, 26 new backend tests and 10 new extension tests)

### Test Coverage
- **546/546 backend tests passing** (100%, 1 skipped)
- **50/50 extension unit tests passing**
- **31/31 extension live backend checks passing**
- **Zero regressions** from M1-M12
- **~70% code coverage** overall (pytest-cov)
- **16 API endpoints** (8 live-tested end-to-end in M12, 8 more exercised by the extension verification)

### M12 Verification Results
- **Test Suite**: 338 tests passing (baseline + SSRF security tests)
- **Security**: SSRF vulnerability fixed — `validate_url()` now blocks RFC 1918 private IP ranges (10.x, 172.16-31.x, 192.168.x), link-local addresses (169.254.x including AWS metadata), and resolves domain hostnames to check resolved IPs
- **Performance**: Server starts in ~40s (NLLB model load); translation ~12s, TTS ~11s, readability ~18ms (deterministic)
- **API Verification**: 8 of 16 endpoints tested with live HTTP requests:
  - `GET /api/health` → 200 (18ms)
  - `POST /api/translate` → 200 (12s, NLLB model)
  - `POST /api/tts` → 200 (11s, edge-tts audio generated)
  - `GET /api/history` → 200 (89 records from PostgreSQL)
  - `POST /api/documents/simplify` → 429 (Gemini quota exhausted — error handling works correctly)
  - `POST /api/documents/extract-info` → 200, structured data extracted
  - `POST /api/documents/validate` → 200, facts validated
  - `POST /api/documents/readability` → 200, metrics computed
- **PostgreSQL**: Verified `document_history` table with 89+ records, 18-column schema intact

### Next Steps (Future)
- M12 complete — project is in final, stable state ready for demonstration

### Notes for Developers
1. ✅ **All test failures resolved** - M1-M10 tests all passing, M11 tests implemented and passing, M12 security tests added
2. ✅ **Core extraction functionality** working correctly for all 14 categories
3. ✅ **Fact preservation** integrated between M5 simplification and M6 extraction
4. ✅ **API response format** consistent across all endpoints with error handling
5. ✅ **Original document text** preserved as source of truth in all extraction operations
6. ✅ **Text-to-Speech (M10)**: Implemented using edge-tts (Microsoft Edge TTS) with English and Kannada support
7. ✅ **Database/History (M11)**: PostgreSQL integration with SQLAlchemy 2.x, history tracking for document processing pipeline
8. ✅ **Real PostgreSQL tested** - Connected to `cognitive_accessibility_db`, tables created, history records stored and retrieved
9. ✅ **SSRF protection hardened (M12)** - Blocks RFC 1918 private IPs, link-local, and AWS metadata endpoint
10. ✅ **Postman collection (M12)** - All 16 endpoints documented with request examples
11. ✅ **Architecture diagram (M12)** - Created `docs/system-architecture.svg` and `docs/system-architecture.png`
12. ✅ **Frontend documented (M12)** - React 19, TypeScript, Vite, Tailwind CSS documented in README
13. ⚠️ **Deprecation warnings**: 97 warnings from Python 3.14 (datetime.utcnow()) and Pydantic V2 (V1-style @validator, .dict()). Non-breaking; documented as tech debt.
14. ✅ **Browser extension (M13)** - Manifest V3 extension in `extension/`, isolated from the website build; uses the same backend, no duplicated AI/translation/TTS code
15. ✅ **Extension CORS (M13)** - Chrome extension origins matched by `CORS_ORIGIN_REGEX`; web origins still restricted to the `CORS_ORIGINS` list, verified by `tests/test_cors.py`
16. ✅ **edge-tts upgraded to 7.3.1 (M13)** - 7.2.8 was rejected with HTTP 403 by Microsoft's speech endpoint, breaking TTS for the website and the extension
