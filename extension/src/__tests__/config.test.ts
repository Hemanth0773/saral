import test from 'node:test';
import assert from 'node:assert/strict';

import {
  ALLOWED_FILE_EXTENSIONS,
  DEFAULT_BASE_URL,
  MAX_FILE_SIZE_MB,
  SUPPORTED_LANGUAGES,
  UNAVAILABLE_LANGUAGES,
  formatBytes,
  getFileExtension,
  isSupportedLanguage,
  joinUrl,
  toHostPermission,
  validateBaseUrl,
} from '../shared/config.ts';

test('validateBaseUrl accepts a normal backend address', () => {
  const result = validateBaseUrl('http://127.0.0.1:8000');
  assert.equal(result.ok, true);
  assert.equal(result.value, 'http://127.0.0.1:8000');
});

test('validateBaseUrl strips trailing slashes', () => {
  const result = validateBaseUrl('https://saral.example.com/');
  assert.equal(result.ok, true);
  assert.equal(result.value, 'https://saral.example.com');
});

test('validateBaseUrl keeps a path prefix', () => {
  const result = validateBaseUrl('https://example.com/saral/');
  assert.equal(result.ok, true);
  assert.equal(result.value, 'https://example.com/saral');
});

test('validateBaseUrl rejects empty, relative and non-http URLs', () => {
  assert.equal(validateBaseUrl('').ok, false);
  assert.equal(validateBaseUrl('   ').ok, false);
  assert.equal(validateBaseUrl('127.0.0.1:8000').ok, false);
  assert.equal(validateBaseUrl('file:///etc/passwd').ok, false);
  assert.equal(validateBaseUrl('javascript:alert(1)').ok, false);
  assert.equal(validateBaseUrl('ftp://example.com').ok, false);
});

test('validateBaseUrl explains why the address was rejected', () => {
  const result = validateBaseUrl('file:///etc/passwd');
  assert.equal(result.ok, false);
  assert.match(result.message ?? '', /http/i);
});

test('joinUrl builds absolute API paths', () => {
  assert.equal(joinUrl('http://127.0.0.1:8000', '/api/tts'), 'http://127.0.0.1:8000/api/tts');
  assert.equal(joinUrl('http://127.0.0.1:8000/', '/api/tts'), 'http://127.0.0.1:8000/api/tts');
  assert.equal(joinUrl('http://127.0.0.1:8000', 'api/tts'), 'http://127.0.0.1:8000/api/tts');
});

test('toHostPermission produces a Chrome host pattern', () => {
  assert.equal(toHostPermission('http://127.0.0.1:8000'), 'http://127.0.0.1:8000/*');
  assert.equal(toHostPermission('https://saral.example.com'), 'https://saral.example.com/*');
  assert.equal(toHostPermission('not a url'), '');
});

test('formatBytes renders human readable sizes', () => {
  assert.equal(formatBytes(0), '0 B');
  assert.equal(formatBytes(512), '512 B');
  assert.equal(formatBytes(2048), '2 KB');
  assert.equal(formatBytes(5 * 1024 * 1024), '5.0 MB');
});

test('getFileExtension lowercases the extension', () => {
  assert.equal(getFileExtension('notice.PDF'), 'pdf');
  assert.equal(getFileExtension('scan.jpeg'), 'jpeg');
  assert.equal(getFileExtension('noextension'), '');
  assert.equal(getFileExtension('trailing.'), '');
});

test('supported languages match what the backend accepts', () => {
  assert.deepEqual(
    SUPPORTED_LANGUAGES.map((language) => language.code),
    ['en', 'kn'],
  );
  assert.equal(isSupportedLanguage('en'), true);
  assert.equal(isSupportedLanguage('kn'), true);
  assert.equal(isSupportedLanguage('hi'), false);
});

test('Hindi is advertised as unavailable rather than silently supported', () => {
  const hindi = UNAVAILABLE_LANGUAGES.find((language) => language.code === 'hi');
  assert.ok(hindi, 'Hindi should be listed as an unavailable language');
  assert.match(hindi.reason, /English and Kannada/);
  assert.equal(isSupportedLanguage(hindi.code), false);
});

test('the file allow list mirrors the backend validation', () => {
  assert.deepEqual([...ALLOWED_FILE_EXTENSIONS], ['pdf', 'txt', 'docx', 'doc', 'jpg', 'jpeg', 'png']);
  assert.equal(MAX_FILE_SIZE_MB, 10);
});

test('the default backend address is the local development server', () => {
  assert.equal(DEFAULT_BASE_URL, 'http://127.0.0.1:8000');
});
