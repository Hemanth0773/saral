import test from 'node:test';
import assert from 'node:assert/strict';

import { performApiRequest } from '../background/api.ts';
import type { ApiRequestMessage } from '../types/messages.ts';

const originalFetch = globalThis.fetch;

function stubFetch(handler: (url: string, init: RequestInit) => Promise<Response>) {
  globalThis.fetch = handler as unknown as typeof fetch;
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

test.afterEach(() => {
  globalThis.fetch = originalFetch;
});

const simplifyRequest: ApiRequestMessage = {
  kind: 'api-request',
  path: '/api/documents/simplify',
  method: 'POST',
  body: JSON.stringify({ text: 'hello', target_grade_level: 5 }),
};

test('a successful response is returned as a typed envelope', async () => {
  stubFetch(async () => jsonResponse({ success: true, simplified_text: 'hello there' }));

  const result = await performApiRequest('http://127.0.0.1:8000', simplifyRequest);

  assert.equal(result.ok, true);
  if (result.ok) {
    assert.equal((result.data as { simplified_text: string }).simplified_text, 'hello there');
  }
});

test('the base URL and the JSON body are forwarded to the backend', async () => {
  let seenUrl = '';
  let seenInit: RequestInit | undefined;

  stubFetch(async (url, init) => {
    seenUrl = url;
    seenInit = init;
    return jsonResponse({ success: true });
  });

  await performApiRequest('http://127.0.0.1:8000', simplifyRequest);

  assert.equal(seenUrl, 'http://127.0.0.1:8000/api/documents/simplify');
  assert.equal(seenInit?.method, 'POST');
  assert.equal(seenInit?.body, JSON.stringify({ text: 'hello', target_grade_level: 5 }));
  const headers = seenInit?.headers as Record<string, string>;
  assert.equal(headers['Content-Type'], 'application/json');
});

test('a backend error keeps the backend error code and message', async () => {
  stubFetch(async () =>
    jsonResponse(
      { success: false, error: { code: 'LLM_QUOTA_EXHAUSTED', message: 'API quota exhausted.' } },
      429,
    ),
  );

  const result = await performApiRequest('http://127.0.0.1:8000', simplifyRequest);

  assert.equal(result.ok, false);
  if (!result.ok) {
    assert.equal(result.error.status, 429);
    assert.equal(result.error.code, 'LLM_QUOTA_EXHAUSTED');
    assert.equal(result.error.message, 'API quota exhausted.');
  }
});

test('a nested detail error is also understood', async () => {
  stubFetch(async () => jsonResponse({ detail: { code: 'INVALID_URL', message: 'Local URLs are not allowed' } }, 400));

  const result = await performApiRequest('http://127.0.0.1:8000', simplifyRequest);

  assert.equal(result.ok, false);
  if (!result.ok) {
    assert.equal(result.error.code, 'INVALID_URL');
    assert.equal(result.error.status, 400);
  }
});

test('an unreadable success body is reported instead of being ignored', async () => {
  stubFetch(async () => new Response('not json at all', { status: 200 }));

  const result = await performApiRequest('http://127.0.0.1:8000', simplifyRequest);

  assert.equal(result.ok, false);
  if (!result.ok) {
    assert.equal(result.error.code, 'INVALID_RESPONSE');
  }
});

test('an unreachable backend is reported as a transport failure', async () => {
  stubFetch(async () => {
    throw new TypeError('Failed to fetch');
  });

  const result = await performApiRequest('http://127.0.0.1:8000', simplifyRequest);

  assert.equal(result.ok, false);
  if (!result.ok) {
    assert.equal(result.error.status, 0);
    assert.equal(result.error.code, 'BACKEND_UNAVAILABLE');
    assert.match(result.error.message, /127\.0\.0\.1:8000/);
  }
});

test('a cancelled request is reported as a timeout', async () => {
  stubFetch(async () => {
    const error = new Error('aborted');
    error.name = 'AbortError';
    throw error;
  });

  const result = await performApiRequest('http://127.0.0.1:8000', simplifyRequest);

  assert.equal(result.ok, false);
  if (!result.ok) {
    assert.equal(result.error.code, 'REQUEST_TIMEOUT');
  }
});

test('a multipart upload is sent without a manual content type header', async () => {
  let seenInit: RequestInit | undefined;
  stubFetch(async (_url, init) => {
    seenInit = init;
    return jsonResponse({ success: true, text: 'extracted' });
  });

  const formData = new FormData();
  formData.append('file', new Blob(['hello']), 'notice.pdf');

  await performApiRequest('http://127.0.0.1:8000', {
    kind: 'api-request',
    path: '/api/documents/extract',
    method: 'POST',
    body: formData,
  });

  const headers = seenInit?.headers as Record<string, string>;
  assert.equal(headers['Content-Type'], undefined);
  assert.ok(seenInit?.body instanceof FormData);
});

test('performApiRequest reconstructs FormData from serialized multipart data', async () => {
  let seenBody: unknown = undefined;
  let seenContentType: string | undefined = undefined;
  stubFetch(async (_url, init) => {
    seenBody = init.body;
    seenContentType = (init.headers as Record<string, string>)?.['Content-Type'];
    return jsonResponse({ success: true, text: 'extracted' });
  });

  const base64 = btoa('hello');
  await performApiRequest('http://127.0.0.1:8000', {
    kind: 'api-request',
    path: '/api/documents/extract',
    method: 'POST',
    multipart: { field: 'file', filename: 'notice.pdf', type: 'application/pdf', data: base64 },
  });

  assert.ok(seenBody instanceof FormData, 'the body must be a FormData instance');
  assert.equal(seenContentType, undefined, 'no manual Content-Type header must be set');
  const formData = seenBody as FormData;
  const file = formData.get('file');
  assert.ok(file instanceof File, 'the file field must be a File');
  if (file instanceof File) {
    assert.equal(file.name, 'notice.pdf');
    assert.equal(file.type, 'application/pdf');
    const text = await file.text();
    assert.equal(text, 'hello');
  }
});
