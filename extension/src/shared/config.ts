/**
 * Extension-wide configuration and limits.
 *
 * Every limit here is derived from the actual backend configuration
 * (`backend/app/core/config.py` and `backend/app/core/security.py`) so the
 * popup never sends a payload the server will reject.
 */

/** Backend used during local development. Overridable at runtime. */
export const DEFAULT_BASE_URL = 'http://127.0.0.1:8000';

/** `chrome.storage.local` key holding the persisted extension configuration. */
export const STORAGE_KEY = 'saralConfig';

/** `backend/app/core/config.py` -> `MAX_FILE_SIZE_MB` (default 10). */
export const MAX_FILE_SIZE_MB = 10;
export const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

/** `backend/app/core/security.py` -> `validate_file_upload` allow-list. */
export const ALLOWED_FILE_EXTENSIONS = ['pdf', 'txt', 'docx', 'doc', 'jpg', 'jpeg', 'png'] as const;

/** `backend/app/schemas/simplification.py` -> `SimplificationRequest.text` max length. */
export const MAX_SIMPLIFY_TEXT_LENGTH = 50_000;

/** `backend/app/core/config.py` -> `MAX_DOCUMENT_LENGTH` (used by translate/tts). */
export const MAX_DOCUMENT_LENGTH = 100_000;

/** Reading-grade target offered to the backend (1-12). */
export const TARGET_GRADE_LEVEL = 5;

export interface LanguageOption {
  code: string;
  label: string;
  native: string;
}

/**
 * Languages the Saral backend can actually produce.
 * `backend/app/schemas/translation.py` and `backend/app/schemas/tts.py` both
 * validate against `['en', 'kn']` only.
 */
export const SUPPORTED_LANGUAGES: LanguageOption[] = [
  { code: 'en', label: 'English', native: 'English' },
  { code: 'kn', label: 'Kannada', native: 'ಕನ್ನಡ' },
];

export interface UnavailableLanguageOption extends LanguageOption {
  reason: string;
}

/**
 * Languages shown in the UI but explicitly marked as unavailable, because the
 * current backend rejects their language codes. We never silently fall back to
 * another language and label it as this one.
 */
export const UNAVAILABLE_LANGUAGES: UnavailableLanguageOption[] = [
  {
    code: 'hi',
    label: 'Hindi',
    native: 'हिन्दी',
    reason: 'Not available yet — the Saral backend translation model currently supports English and Kannada only.',
  },
];

export function isSupportedLanguage(code: string): boolean {
  return SUPPORTED_LANGUAGES.some((language) => language.code === code);
}

export interface BaseUrlValidation {
  ok: boolean;
  value?: string;
  message?: string;
}

/**
 * Normalises and validates a user supplied backend base URL.
 * Only absolute http(s) URLs are accepted; the trailing slash is removed so
 * path concatenation stays predictable.
 */
export function validateBaseUrl(raw: string): BaseUrlValidation {
  const trimmed = (raw ?? '').trim();
  if (!trimmed) {
    return { ok: false, message: 'Enter the backend address, for example http://127.0.0.1:8000' };
  }

  let parsed: URL;
  try {
    parsed = new URL(trimmed);
  } catch {
    return { ok: false, message: 'That is not a valid URL. Use a full address such as http://127.0.0.1:8000' };
  }

  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    return { ok: false, message: 'Only http:// and https:// addresses are supported.' };
  }

  if (!parsed.hostname) {
    return { ok: false, message: 'The address is missing a host name.' };
  }

  const normalised = trimmed.replace(/\/+$/, '');
  return { ok: true, value: normalised };
}

/** Joins a backend base URL with an absolute API path. */
export function joinUrl(baseUrl: string, path: string): string {
  const base = baseUrl.replace(/\/+$/, '');
  const suffix = path.startsWith('/') ? path : `/${path}`;
  return `${base}${suffix}`;
}

/** Returns the origin of a base URL in the format Chrome expects for host permissions. */
export function toHostPermission(baseUrl: string): string {
  try {
    const parsed = new URL(baseUrl);
    return `${parsed.protocol}//${parsed.host}/*`;
  } catch {
    return '';
  }
}

export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function getFileExtension(filename: string): string {
  const index = filename.lastIndexOf('.');
  if (index < 0 || index === filename.length - 1) return '';
  return filename.slice(index + 1).toLowerCase();
}
