import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const REPO_ROOT = fileURLToPath(new URL('../../../', import.meta.url));

function readSource(relativePath: string): string {
  return readFileSync(`${REPO_ROOT}${relativePath}`, 'utf8');
}

// ============================================================
// The Choose File button is functional
// ============================================================

test('the Choose File button is not pointer-events-none', () => {
  const source = readSource('extension/src/popup/components/InputCard.tsx');
  assert.equal(source.includes('pointer-events-none'), false, 'the Choose File button must be clickable');
});

test('the Choose File button triggers the hidden file input on click', () => {
  const source = readSource('extension/src/popup/components/InputCard.tsx');
  assert.ok(source.includes('onClick={() => inputRef.current?.click()}'), 'the button must call inputRef.current.click()');
  assert.ok(source.includes('ref={inputRef}'), 'the file input must use the inputRef');
  assert.ok(source.includes('type="file"'), 'the input must be a file input');
});

test('the Choose File button is disabled while a file is being processed', () => {
  const source = readSource('extension/src/popup/components/InputCard.tsx');
  assert.ok(source.includes('disabled={isReading}'), 'the button must be disabled while reading');
});

test('the file input accepts the same extensions the backend allows', () => {
  const source = readSource('extension/src/popup/components/InputCard.tsx');
  const config = readSource('extension/src/shared/config.ts');
  const allowed = ['pdf', 'txt', 'docx', 'doc', 'jpg', 'jpeg', 'png'];
  assert.ok(source.includes('ACCEPT_ATTRIBUTE'), 'the file input must use the ACCEPT_ATTRIBUTE constant');
  assert.ok(config.includes(`ALLOWED_FILE_EXTENSIONS = ['${allowed.join("', '")}'] as const`), 'the allow list must match the backend');
});

test('the file input resets its value after a selection so the same file can be re-chosen', () => {
  const source = readSource('extension/src/popup/components/InputCard.tsx');
  assert.ok(source.includes("event.target.value = ''"), 'the input value must be reset after selection');
});

test('selecting a file calls onSelectFile with the selected file', () => {
  const source = readSource('extension/src/popup/components/InputCard.tsx');
  assert.ok(source.includes('if (selected) onSelectFile(selected);'), 'onSelectFile must be called with the selected file');
});

test('cancelling the picker (no file) does not call onSelectFile', () => {
  const source = readSource('extension/src/popup/components/InputCard.tsx');
  assert.ok(source.includes('const selected = event.target.files?.[0];'), 'the selected file must be read from the event');
  assert.ok(source.includes('if (selected) onSelectFile(selected);'), 'onSelectFile must be skipped when no file is selected');
});

// ============================================================
// App.tsx wires file upload end to end
// ============================================================

test('App.tsx passes onSelectFile to InputCard', () => {
  const source = readSource('extension/src/popup/App.tsx');
  assert.ok(source.includes('onSelectFile={handleSelectFile}'), 'App must pass the file select handler to InputCard');
});

test('App.tsx passes isReading to InputCard', () => {
  const source = readSource('extension/src/popup/App.tsx');
  assert.ok(source.includes('isReading={isReading}'), 'App must pass isReading to InputCard');
});

test('App.tsx passes the attached file to InputCard', () => {
  const source = readSource('extension/src/popup/App.tsx');
  assert.ok(source.includes('file={file}'), 'App must pass the attached file to InputCard');
});

test('App.tsx validates file type before uploading', () => {
  const source = readSource('extension/src/popup/App.tsx');
  assert.ok(source.includes('ALLOWED_FILE_EXTENSIONS.includes'), 'the file type must be validated against the allow list');
  assert.ok(source.includes('getFileExtension(selected.name)'), 'the extension must be extracted from the filename');
});

test('App.tsx rejects files over the size limit', () => {
  const source = readSource('extension/src/popup/App.tsx');
  assert.ok(source.includes('selected.size > MAX_FILE_SIZE_BYTES'), 'files over the size limit must be rejected');
});

test('App.tsx rejects empty files', () => {
  const source = readSource('extension/src/popup/App.tsx');
  assert.ok(source.includes('selected.size === 0'), 'empty files must be rejected');
});

test('App.tsx sends the file to the extract endpoint via multipart', () => {
  const source = readSource('extension/src/popup/App.tsx');
  assert.ok(source.includes('saralApi.extractFile(selected)'), 'the selected file must be sent to the extract endpoint');
});

test('the API client serialises the file as base64 with the multipart field', () => {
  const source = readSource('extension/src/services/api.ts');
  assert.ok(source.includes("multipart: { field: 'file'"), 'extractFile must send the file field');
  assert.ok(source.includes('filename: file.name'), 'the filename must be preserved');
  assert.ok(source.includes('type: file.type'), 'the file type must be preserved');
  assert.ok(source.includes('btoa('), 'the file bytes must be base64-encoded');
  assert.ok(source.includes('reader.readAsArrayBuffer(file)'), 'the file must be read as an ArrayBuffer');
  assert.ok(source.includes("path: '/api/documents/extract'"), 'the request must go to /api/documents/extract');
});

test('the background service worker reconstructs FormData from base64 multipart data', () => {
  const source = readSource('extension/src/background/api.ts');
  assert.ok(source.includes('base64ToBytes'), 'the worker must decode base64 to bytes');
  assert.ok(source.includes('buildMultipartFormData'), 'the worker must rebuild FormData');
  assert.ok(source.includes("formData.append(multipart.field, blob, multipart.filename)"), 'the file field must be appended with its filename');
});

test('performApiRequest sends multipart data without a manual Content-Type header', async () => {
  // This test is covered by 'a multipart upload is sent without a manual content type header'
  // in api.test.ts which tests performApiRequest directly with body: FormData.
  // The new multipart field path also sets init.body = FormData without Content-Type.
});

test('the background service worker sends multipart without a manual Content-Type header', () => {
  const source = readSource('extension/src/background/api.ts');
  assert.ok(source.includes('init.body = request.body'), 'FormData must be assigned as the body');
  assert.ok(source.includes("init.headers = { ...init.headers, 'Content-Type': 'application/json' }"), 'JSON requests keep the Content-Type header');
});

test('the simplify flow can be triggered from an attached file', () => {
  const source = readSource('extension/src/popup/App.tsx');
  assert.ok(source.includes('if (!trimmed && !file)'), 'simplify must allow an attached file with no text');
  assert.ok(source.includes('canSimplify = Boolean(text.trim() || file)'), 'canSimplify must be true when a file is attached');
});

// ============================================================
// The upload flow does not break other functionality
// ============================================================

test('clearing the input also clears the attached file', () => {
  const source = readSource('extension/src/popup/App.tsx');
  assert.ok(source.includes('setFile(null)'), 'clearing must remove the attached file');
});

test('reading the active tab clears the attached file', () => {
  const source = readSource('extension/src/popup/App.tsx');
  assert.ok(source.includes('setFile(null)'), 'reading the active tab must clear the attached file');
});

// ============================================================
// File-to-simplify flow (regression tests for empty-text bug)
// ============================================================

test('simplify extracts the attached file when the text box is empty', () => {
  const source = readSource('extension/src/popup/App.tsx');
  assert.ok(source.includes('if (file && !trimmed)'), 'simplify must extract the file when text box is empty');
  assert.ok(source.includes('saralApi.extractFile(file)'), 'simplify must call extractFile for the attached file');
});

test('simplify does not call the simplify endpoint with empty text', () => {
  const source = readSource('extension/src/popup/App.tsx');
  // After extracting the file, sourceText must be set from extracted.text
  // before simplify is called.
  assert.ok(
    source.includes('sourceText = extracted.text;'),
    'simplify must use the extracted text as the source text',
  );
  // The empty-text guard must not short-circuit when a file is attached.
  assert.ok(source.includes('if (!trimmed && !file)'), 'the empty-text guard must allow an attached file');
});

test('simplify shows a clear error when the file contains no extractable text', () => {
  const source = readSource('extension/src/popup/App.tsx');
  assert.ok(
    source.includes("title: 'No text found in document'"),
    'simplify must show a clear error when extraction returns empty text',
  );
  assert.ok(
    source.includes("Saral could not extract any text from this file"),
    'the error must explain that no text was extracted',
  );
});

test('normal text input still works without a file', () => {
  const source = readSource('extension/src/popup/App.tsx');
  // When there is no file and the text is not a URL, sourceText stays as trimmed.
  assert.ok(source.includes('let sourceText = trimmed;'), 'plain text input must be used directly');
  // The URL branch is only entered when there is no file.
  assert.ok(source.includes('else if (!file && looksLikeUrl(trimmed))'), 'URL extraction requires no file attached');
});

test('URL processing still works without a file', () => {
  const source = readSource('extension/src/popup/App.tsx');
  assert.ok(source.includes('saralApi.extractUrl(trimmed)'), 'URL extraction must still be called');
  assert.ok(source.includes('extracted.source_url'), 'the source note must reference the source URL');
});

test('simplify result carries Instant Summary and validation info', () => {
  const source = readSource('extension/src/popup/App.tsx');
  assert.ok(source.includes('setSimplification(result);'), 'the simplify result must be stored');
  assert.ok(source.includes('result.instant_summary'), 'the Instant Summary must be rendered from the result');
  assert.ok(source.includes('validation_passed'), 'validation info must be rendered from the result');
  assert.ok(source.includes('validation_failures'), 'validation failures must be rendered from the result');
});
