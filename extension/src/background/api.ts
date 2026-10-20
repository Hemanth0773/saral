/**
 * Typed HTTP client used by the background service worker.
 *
 * All backend traffic goes through here so that the base URL, timeout and
 * error normalisation live in exactly one place. The service worker is used
 * (instead of the popup) so requests survive the popup being closed and so the
 * extension origin is the only caller the backend has to allow.
 */
import { joinUrl } from '../shared/config';
import { SaralApiError } from '../shared/errors';
import type { ApiRequestMessage, SaralEnvelope } from '../types/messages';

/** Generous enough for cold LLM / NLLB / TTS calls, short enough to fail visibly. */
export const REQUEST_TIMEOUT_MS = 90_000;

function isFormData(body: unknown): body is FormData {
  return typeof FormData !== 'undefined' && body instanceof FormData;
}

function extractErrorMessage(payload: unknown, status: number): { code: string; message: string } {
  if (payload && typeof payload === 'object') {
    const record = payload as Record<string, unknown>;
    const error = record.error as { code?: unknown; message?: unknown } | undefined;
    if (error && typeof error.message === 'string' && error.message.trim()) {
      return {
        code: typeof error.code === 'string' && error.code ? error.code : 'REQUEST_FAILED',
        message: error.message.trim(),
      };
    }
    if (typeof record.detail === 'string' && record.detail.trim()) {
      return { code: 'REQUEST_FAILED', message: record.detail.trim() };
    }
    if (record.detail && typeof record.detail === 'object') {
      const detail = record.detail as { code?: unknown; message?: unknown };
      if (typeof detail.message === 'string' && detail.message.trim()) {
        return {
          code: typeof detail.code === 'string' && detail.code ? detail.code : 'REQUEST_FAILED',
          message: detail.message.trim(),
        };
      }
    }
    if (typeof record.message === 'string' && record.message.trim()) {
      return { code: 'REQUEST_FAILED', message: record.message.trim() };
    }
  }
  return { code: 'REQUEST_FAILED', message: `Request failed with status ${status}` };
}

/**
 * Executes a single backend request and always resolves to an envelope —
 * transport failures are converted into a `SaralError` instead of throwing.
 */
export async function performApiRequest(
  baseUrl: string,
  request: ApiRequestMessage,
): Promise<SaralEnvelope<unknown>> {
  const url = joinUrl(baseUrl, request.path);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const init: RequestInit = {
      method: request.method,
      signal: controller.signal,
      headers: { Accept: 'application/json' },
    };

    if (request.body !== undefined) {
      if (isFormData(request.body)) {
        // Let the runtime set the multipart boundary.
        init.body = request.body;
      } else {
        init.body = request.body;
        init.headers = { ...init.headers, 'Content-Type': 'application/json' };
      }
    }

    const response = await fetch(url, init);
    const rawText = await response.text();
    let payload: unknown = undefined;
    if (rawText) {
      try {
        payload = JSON.parse(rawText);
      } catch {
        payload = undefined;
      }
    }

    if (!response.ok) {
      const { code, message } = extractErrorMessage(payload, response.status);
      return {
        ok: false,
        error: { code, message, status: response.status },
      };
    }

    if (payload === undefined) {
      return {
        ok: false,
        error: {
          code: 'INVALID_RESPONSE',
          message: 'The backend returned a response Saral could not read.',
          status: response.status,
        },
      };
    }

    return { ok: true, data: payload };
  } catch (error) {
    // `fetch` rejects with a DOMException named AbortError when the request is
    // cancelled, but other runtimes surface a plain Error with the same name.
    const errorName = error instanceof Error ? error.name : '';
    if (errorName === 'AbortError' || errorName === 'TimeoutError') {
      return {
        ok: false,
        error: {
          code: 'REQUEST_TIMEOUT',
          message: 'The backend took too long to respond. Please try again.',
          status: 0,
        },
      };
    }
    return {
      ok: false,
      error: {
        code: 'BACKEND_UNAVAILABLE',
        message: `Saral could not reach the backend at ${baseUrl}. Make sure it is running.`,
        status: 0,
      },
    };
  } finally {
    clearTimeout(timeout);
  }
}

export { SaralApiError };
