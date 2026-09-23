const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

type ApiErrorPayload = {
  detail?: unknown;
  error?: {
    code?: string;
    message?: string;
  };
  message?: string;
};

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(message: string, status: number, code = 'REQUEST_FAILED') {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

function getErrorMessage(payload: ApiErrorPayload, status: number) {
  if (payload?.error?.message) {
    return payload.error.message;
  }

  if (payload?.message) {
    return payload.message;
  }

  if (typeof payload?.detail === 'string') {
    return payload.detail;
  }

  if (payload?.error?.code) {
    return payload.error.code.replace(/_/g, ' ');
  }

  return `Request failed with status ${status}`;
}

async function requestJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
        ...options.headers,
      },
    });
  } catch {
    throw new ApiError(
      'Unable to connect to the Saral backend. Make sure it is running on port 8000.',
      0,
      'BACKEND_UNAVAILABLE',
    );
  }

  const payload = (await response.json().catch(() => ({}))) as ApiErrorPayload;

  if (!response.ok) {
    const message = getErrorMessage(payload, response.status);
    const code = payload?.error?.code || (payload?.detail && typeof payload.detail === 'object' ? 'REQUEST_FAILED' : undefined);
    throw new ApiError(message, response.status, code || 'REQUEST_FAILED');
  }

  return payload as T;
}

export type DocumentExtractionResponse = {
  success: boolean;
  document_id: string;
  filename?: string;
  source_url?: string;
  language: string;
  extraction_method: string;
  text: string;
  text_truncated: boolean;
  metadata: {
    document_id: string;
    filename?: string | null;
    language: string;
    page_count: number;
    word_count: number;
    extraction_method: string;
    extracted_at: string;
  };
};

export type SimplificationResponse = {
  success: boolean;
  document_id: string;
  original_text: string;
  simplified_text: string;
  target_grade_level: number;
  model_used: string;
  processing_time_ms: number;
  sections: Array<{
    title?: string;
    original_text: string;
    simplified_text: string;
    grade_level_improvement?: number;
  }>;
  preserved_facts: Array<{
    fact_type: string;
    value: string;
    source_text: string;
    preserved_in_simplified: boolean;
  }>;
  key_terms: string[];
  validation_passed: boolean;
  validation_failures: string[];
  metadata: Record<string, unknown>;
};

export type TranslationResponse = {
  success: boolean;
  translated_text: string;
  source_language: string;
  target_language: string;
  model_used: string;
  character_count: number;
  translated_character_count: number;
};

export type TTSResponse = {
  success: boolean;
  audio_url: string;
  filename: string;
  language: string;
  voice: string;
  text_length: number;
  file_size_bytes: number;
  content_type: string;
  processing_time_ms: number;
};

export function extractDocument(file: File) {
  const formData = new FormData();
  formData.append('file', file);

  return requestJson<DocumentExtractionResponse>('/api/documents/extract', {
    method: 'POST',
    body: formData,
  });
}

export function extractDocumentUrl(url: string) {
  return requestJson<DocumentExtractionResponse>('/api/documents/url', {
    method: 'POST',
    body: JSON.stringify({ url }),
  });
}

export function simplifyDocument(text: string, targetGradeLevel = 5) {
  return requestJson<SimplificationResponse>('/api/documents/simplify', {
    method: 'POST',
    body: JSON.stringify({
      text,
      target_grade_level: targetGradeLevel,
    }),
  });
}

export function translateText(text: string, sourceLanguage: string, targetLanguage: string) {
  return requestJson<TranslationResponse>('/api/translate', {
    method: 'POST',
    body: JSON.stringify({
      text,
      source_language: sourceLanguage,
      target_language: targetLanguage,
    }),
  });
}

export function synthesizeSpeech(text: string, language = 'en') {
  return requestJson<TTSResponse>('/api/tts', {
    method: 'POST',
    body: JSON.stringify({
      text,
      language,
      speed: 1,
    }),
  });
}

export function getAudioUrl(audioUrl: string) {
  if (/^https?:\/\//i.test(audioUrl)) {
    return audioUrl;
  }

  return `${API_BASE_URL}${audioUrl}`;
}

export { API_BASE_URL };
