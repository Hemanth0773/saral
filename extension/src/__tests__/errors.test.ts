import test from 'node:test';
import assert from 'node:assert/strict';

import { SaralApiError, describeError, toSaralError } from '../shared/errors.ts';

test('a transport failure is reported as an unreachable backend', () => {
  const friendly = describeError({ code: 'BACKEND_UNAVAILABLE', message: '', status: 0 });
  assert.equal(friendly.title, 'Backend unreachable');
  assert.equal(friendly.retryable, true);
});

test('HTTP 429 is reported as a quota problem and is retryable', () => {
  const friendly = describeError({
    code: 'LLM_QUOTA_EXHAUSTED',
    message: 'API quota exhausted. Please try again later.',
    status: 429,
  });
  assert.equal(friendly.title, 'Service quota exhausted');
  assert.equal(friendly.retryable, true);
  assert.match(friendly.message, /quota/i);
});

test('HTTP 503 is reported as a service outage and is retryable', () => {
  const friendly = describeError({
    code: 'TRANSLATION_SERVICE_ERROR',
    message: 'Translation service unavailable. Please try again later.',
    status: 503,
  });
  assert.equal(friendly.title, 'Service unavailable');
  assert.equal(friendly.retryable, true);
});

test('HTTP 400 and 422 keep the backend explanation', () => {
  const badRequest = describeError({
    code: 'INVALID_FILE_TYPE',
    message: 'File type not allowed.',
    status: 400,
  });
  assert.equal(badRequest.title, 'Invalid request');
  assert.equal(badRequest.message, 'File type not allowed.');
  assert.equal(badRequest.retryable, false);

  const validation = describeError({
    code: 'VALIDATION_ERROR',
    message: 'text: String should have at least 1 character',
    status: 422,
  });
  assert.equal(validation.title, 'Invalid input');
  assert.equal(validation.retryable, false);
});

test('internal server details never reach the user', () => {
  const friendly = describeError({
    code: 'SERVER_ERROR',
    message: 'Traceback (most recent call last): File "D:\\app\\main.py", line 42',
    status: 500,
  });
  assert.doesNotMatch(friendly.message, /Traceback/);
  assert.doesNotMatch(friendly.message, /D:\\app/);
});

test('a fallback message is used when the backend says nothing useful', () => {
  const friendly = describeError({ code: 'REQUEST_FAILED', message: '', status: 500 });
  assert.equal(friendly.title, 'Server error');
  assert.ok(friendly.message.length > 0);
});

test('toSaralError keeps the code and status of a SaralApiError', () => {
  const error = new SaralApiError('boom', 'LLM_QUOTA_EXHAUSTED', 429);
  const mapped = toSaralError(error);
  assert.deepEqual(mapped, { code: 'LLM_QUOTA_EXHAUSTED', message: 'boom', status: 429 });
});

test('toSaralError handles unknown throwables', () => {
  const mapped = toSaralError('something odd');
  assert.equal(mapped.code, 'UNEXPECTED_ERROR');
  assert.equal(mapped.status, 0);
});
