/**
 * Central error handling: turns backend responses into short, human readable
 * messages. Raw stack traces, file system paths and internal server details
 * are never surfaced to the popup.
 */
import type { SaralError } from '../types/messages';

export class SaralApiError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(message: string, code = 'REQUEST_FAILED', status = 0) {
    super(message);
    this.name = 'SaralApiError';
    this.code = code;
    this.status = status;
  }
}

export interface FriendlyError {
  title: string;
  message: string;
  /** True when retrying the same request could plausibly succeed. */
  retryable: boolean;
}

const STATUS_TITLES: Record<number, string> = {
  400: 'Invalid request',
  404: 'Endpoint not found',
  413: 'File too large',
  422: 'Invalid input',
  429: 'Service quota exhausted',
  500: 'Server error',
  502: 'Bad gateway',
  503: 'Service unavailable',
  504: 'Backend timed out',
};

/** Titles for the backend's own error codes, which are more precise. */
const CODE_TITLES: Record<string, string> = {
  LLM_RATE_LIMITED: 'Rate limit reached',
  LLM_QUOTA_EXHAUSTED: 'Service quota exhausted',
  LLM_SERVICE_UNAVAILABLE: 'Service temporarily unavailable',
  LLM_TIMEOUT: 'Backend timed out',
};

const STATUS_MESSAGES: Record<number, string> = {
  400: 'The backend rejected that request. Check the text, URL or file and try again.',
  404: 'The backend does not have that endpoint. Check the backend address in Saral settings.',
  413: 'That file is larger than the backend accepts.',
  422: 'Some of that content is not valid for this operation. Review it and try again.',
  429: 'The simplification service has run out of quota right now. Wait a moment and retry.',
  500: 'The backend hit an unexpected error while processing. Try again in a moment.',
  502: 'The backend could not be reached through its gateway. Check that it is running.',
  503: 'A backend service is unavailable right now. Try again shortly.',
  504: 'The backend took too long to respond. Try again.',
};

/** Normalises anything thrown inside the extension into a `SaralError`. */
export function toSaralError(error: unknown): SaralError {
  if (error instanceof SaralApiError) {
    return { code: error.code, message: error.message, status: error.status };
  }
  if (error instanceof Error) {
    return { code: 'UNEXPECTED_ERROR', message: error.message, status: 0 };
  }
  return { code: 'UNEXPECTED_ERROR', message: 'An unexpected error occurred.', status: 0 };
}

/**
 * Produces a short title + explanation for the popup banner.
 * The backend's own message is used when it is safe and specific.
 */
export function describeError(error: SaralError): FriendlyError {
  if (error.status === 0) {
    return {
      title: 'Backend unreachable',
      message:
        error.message ||
        'Saral could not reach the backend. Make sure it is running and check the address in settings.',
      retryable: true,
    };
  }

  const title = CODE_TITLES[error.code] ?? STATUS_TITLES[error.status] ?? 'Request failed';
  const fallback = STATUS_MESSAGES[error.status] ?? 'The request could not be completed.';

  // The backend already returns user-safe sentences for these codes.
  const backendMessage = error.message?.trim();
  const useBackendMessage =
    Boolean(backendMessage) &&
    backendMessage.length <= 220 &&
    !/Traceback|File "|site-packages|\/usr\/lib|Exception:/i.test(backendMessage);

  return {
    title,
    message: useBackendMessage ? (backendMessage as string) : fallback,
    retryable: error.status === 0 || error.status === 429 || error.status >= 500,
  };
}
