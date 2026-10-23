/**
 * Internal message contracts used between the popup, the background service
 * worker and the content script.
 */

/** Backend endpoints the extension is allowed to call. */
export type SaralApiPath =
  | '/api/documents/simplify'
  | '/api/documents/extract'
  | '/api/documents/url'
  | '/api/documents/extract-info'
  | '/api/documents/readability'
  | '/api/translate'
  | '/api/tts';

export interface SaralError {
  code: string;
  message: string;
  status: number;
}

export type SaralEnvelope<T> =
  | { ok: true; data: T }
  | { ok: false; error: SaralError };

/** Popup -> background: perform an HTTP call against the configured backend. */
export interface ApiRequestMessage {
  kind: 'api-request';
  path: SaralApiPath;
  method: 'GET' | 'POST';
  /** JSON body (already serialised) or multipart body for file uploads. */
  body?: string | FormData;
  /**
   * Serialized multipart file upload, used instead of `body: FormData` because
   * FormData/File objects do not reliably survive `chrome.runtime.sendMessage`
   * structured cloning. The background service worker reconstructs FormData
   * from these fields before calling `fetch`.
   */
  multipart?: { field: string; filename: string; type: string; data: string };
}

/** Popup -> background: read the current tab and return its readable text. */
export interface ExtractActiveTabMessage {
  kind: 'extract-active-tab';
}

/** Popup -> background: read the persisted extension configuration. */
export interface GetConfigMessage {
  kind: 'get-config';
}

/** Popup -> background: persist a new backend base URL. */
export interface SetConfigMessage {
  kind: 'set-config';
  baseUrl: string;
}

export type BackgroundRequestMessage =
  | ApiRequestMessage
  | ExtractActiveTabMessage
  | GetConfigMessage
  | SetConfigMessage;

export interface ExtensionConfig {
  baseUrl: string;
}

/** Content script -> background: return the readable text of the current page. */
export interface ExtractContentMessage {
  kind: 'extract-content';
}

export type ContentRequestMessage = ExtractContentMessage;

export interface ExtractedContent {
  text: string;
  source: 'selection' | 'page';
  title: string;
  url: string;
  charCount: number;
  truncated: boolean;
}
