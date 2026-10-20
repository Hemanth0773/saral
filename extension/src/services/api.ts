/**
 * Typed client for the Saral backend, as used by the popup.
 *
 * Every call is routed through the background service worker (never directly
 * from the popup) so the configured backend URL, timeouts and error
 * normalisation live in one place.
 */
import { SaralApiError } from '../shared/errors';
import type {
  DocumentExtractionResponse,
  ExtractionResponse,
  ReadabilityResponse,
  SimplificationResponse,
  TranslationResponse,
  TTSResponse,
} from '../types/api';
import type {
  BackgroundRequestMessage,
  ExtractedContent,
  ExtensionConfig,
  SaralApiPath,
  SaralEnvelope,
} from '../types/messages';

async function callBackground<T>(message: BackgroundRequestMessage): Promise<T> {
  let response: SaralEnvelope<T>;
  try {
    response = await chrome.runtime.sendMessage<BackgroundRequestMessage, SaralEnvelope<T>>(message);
  } catch {
    throw new SaralApiError(
      'Saral could not reach its background service. Reload the extension and try again.',
      'NO_BACKGROUND',
      0,
    );
  }

  if (!response) {
    throw new SaralApiError('Saral did not receive a response from the backend.', 'NO_RESPONSE', 0);
  }
  if (!response.ok) {
    throw new SaralApiError(response.error.message, response.error.code, response.error.status);
  }
  return response.data;
}

function post<T>(path: SaralApiPath, body: unknown): Promise<T> {
  return callBackground<T>({
    kind: 'api-request',
    path,
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export const saralApi = {
  /** `POST /api/documents/simplify` */
  simplify(text: string, targetGradeLevel: number): Promise<SimplificationResponse> {
    return post<SimplificationResponse>('/api/documents/simplify', {
      text,
      target_grade_level: targetGradeLevel,
    });
  },

  /** `POST /api/documents/extract-info` — structured facts from the original text. */
  extractInfo(text: string): Promise<ExtractionResponse> {
    return post<ExtractionResponse>('/api/documents/extract-info', {
      text,
      extract_title: true,
      extract_summary: true,
    });
  },

  /** `POST /api/documents/readability` — measured Flesch-Kincaid metrics. */
  readability(
    originalText: string,
    simplifiedText: string,
    targetGradeLevel: number,
  ): Promise<ReadabilityResponse> {
    return post<ReadabilityResponse>('/api/documents/readability', {
      original_text: originalText,
      simplified_text: simplifiedText,
      target_grade_level: targetGradeLevel,
    });
  },

  /** `POST /api/translate` — English <-> Kannada only (backend enforced). */
  translate(text: string, sourceLanguage: string, targetLanguage: string): Promise<TranslationResponse> {
    return post<TranslationResponse>('/api/translate', {
      text,
      source_language: sourceLanguage,
      target_language: targetLanguage,
    });
  },

  /** `POST /api/tts` — English and Kannada voices only (backend enforced). */
  synthesizeSpeech(text: string, language: string, speed = 1): Promise<TTSResponse> {
    return post<TTSResponse>('/api/tts', {
      text,
      language,
      speed,
    });
  },

  /** `POST /api/documents/url` — server side URL fetch (keeps SSRF protection). */
  extractUrl(url: string): Promise<DocumentExtractionResponse> {
    return post<DocumentExtractionResponse>('/api/documents/url', { url });
  },

  /** `POST /api/documents/extract` — multipart upload handled by the backend. */
  extractFile(file: File): Promise<DocumentExtractionResponse> {
    const formData = new FormData();
    formData.append('file', file, file.name);
    return callBackground<DocumentExtractionResponse>({
      kind: 'api-request',
      path: '/api/documents/extract',
      method: 'POST',
      body: formData,
    });
  },

  /** Reads the readable text of the active tab (or the current selection). */
  extractActiveTab(): Promise<ExtractedContent> {
    return callBackground<ExtractedContent>({ kind: 'extract-active-tab' });
  },

  getConfig(): Promise<ExtensionConfig> {
    return callBackground<ExtensionConfig>({ kind: 'get-config' });
  },

  setConfig(baseUrl: string): Promise<ExtensionConfig> {
    return callBackground<ExtensionConfig>({ kind: 'set-config', baseUrl });
  },
};
