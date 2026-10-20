/**
 * Request/response contracts for the Saral FastAPI backend.
 *
 * These mirror `backend/app/schemas/*` one-to-one. Do not invent fields that
 * the backend does not return — the popup renders strictly from these shapes.
 */

/** Shared error envelope used by every backend endpoint. */
export interface ApiErrorBody {
  success: false;
  error: {
    code: string;
    message: string;
  };
}

export interface DocumentMetadata {
  document_id: string;
  filename: string | null;
  language: string;
  page_count: number;
  word_count: number;
  extraction_method: string;
  extracted_at: string;
}

/** `POST /api/documents/extract` and `POST /api/documents/url` */
export interface DocumentExtractionResponse {
  success: boolean;
  document_id: string;
  filename?: string;
  source_url?: string;
  language: string;
  page_count?: number;
  extraction_method: string;
  text: string;
  text_truncated: boolean;
  metadata: DocumentMetadata;
}

export interface PreservedFact {
  fact_type: string;
  value: string;
  source_text: string;
  preserved_in_simplified: boolean;
}

export interface SimplificationSection {
  title?: string | null;
  original_text: string;
  simplified_text: string;
  grade_level_improvement?: number | null;
}

/** One fact of the canonical Instant Summary, built by the backend. */
export interface InstantSummaryItem {
  id: string;
  kind: string;
  label: string;
  value: string;
  severity: string;
}

/** `POST /api/documents/simplify` */
export interface SimplificationResponse {
  success: boolean;
  document_id: string;
  original_text: string;
  simplified_text: string;
  target_grade_level: number;
  model_used: string;
  processing_time_ms: number;
  sections: SimplificationSection[];
  preserved_facts: PreservedFact[];
  key_terms: string[];
  /**
   * The canonical Instant Summary. The website and the extension render this
   * same list, so both interfaces show the same facts.
   */
  instant_summary: InstantSummaryItem[];
  validation_passed: boolean;
  validation_failures: string[];
  metadata: Record<string, unknown>;
}

export interface ExtractedDeadline {
  date: string;
  description?: string | null;
  original_text: string;
}

export interface ExtractedDate {
  date: string;
  description?: string | null;
  original_text: string;
}

export interface ExtractedRequirement {
  requirement: string;
  category?: string | null;
  original_text: string;
}

export interface ExtractedAgeRequirement {
  minimum_age?: number | null;
  maximum_age?: number | null;
  original_text: string;
}

export interface ExtractedDocument {
  name: string;
  description?: string | null;
  original_text: string;
}

export interface ExtractedMonetaryAmount {
  amount: string;
  amount_normalized?: string | null;
  currency?: string | null;
  purpose?: string | null;
  original_text: string;
}

export interface ExtractedPercentage {
  percentage: string;
  value: number;
  purpose?: string | null;
  original_text: string;
}

export interface ExtractedProcedure {
  step_number?: number | null;
  description: string;
  original_text: string;
}

export interface ExtractedCondition {
  condition: string;
  type?: string | null;
  original_text: string;
}

export interface ExtractedContactInfo {
  type: string;
  value: string;
  original_text: string;
}

export interface ExtractedLocation {
  location: string;
  type?: string | null;
  original_text: string;
}

export interface ExtractedOrganization {
  name: string;
  role?: string | null;
  original_text: string;
}

export interface StructuredInformation {
  title?: string | null;
  summary?: string | null;
  deadlines: ExtractedDeadline[];
  important_dates: ExtractedDate[];
  eligibility_requirements: ExtractedRequirement[];
  age_requirements: ExtractedAgeRequirement[];
  required_documents: ExtractedDocument[];
  financial_information: ExtractedMonetaryAmount[];
  percentages: ExtractedPercentage[];
  application_procedure: ExtractedProcedure[];
  important_conditions: ExtractedCondition[];
  contact_information: ExtractedContactInfo[];
  locations: ExtractedLocation[];
  organizations: ExtractedOrganization[];
}

/** `POST /api/documents/extract-info` */
export interface ExtractionResponse {
  success: boolean;
  document_id: string;
  original_text: string;
  structured_information: StructuredInformation;
  extraction_method: string;
  processing_time_ms: number;
  metadata: Record<string, unknown>;
}

export interface ReadabilityMetrics {
  word_count: number;
  sentence_count: number;
  character_count: number;
  syllable_count: number;
  average_sentence_length: number;
  flesch_reading_ease: number | null;
  flesch_kincaid_grade: number | null;
}

export interface ReadabilityComparison {
  grade_level_improvement: number;
  reading_ease_improvement: number;
  sentence_length_reduction: number;
  target_grade_level: number;
  simplified_grade_level: number | null;
  target_achieved: boolean;
}

/** `POST /api/documents/readability` */
export interface ReadabilityResponse {
  success: boolean;
  supported: boolean;
  message?: string | null;
  original?: ReadabilityMetrics | null;
  simplified?: ReadabilityMetrics | null;
  comparison?: ReadabilityComparison | null;
  processing_time_ms: number;
  language: string;
  timestamp: string;
}

/** `POST /api/translate` */
export interface TranslationResponse {
  success: boolean;
  translated_text: string;
  source_language: string;
  target_language: string;
  model_used: string;
  character_count: number;
  translated_character_count: number;
}

/** `POST /api/tts` */
export interface TTSResponse {
  success: boolean;
  audio_url: string;
  filename: string;
  language: string;
  voice: string;
  text_length: number;
  file_size_bytes: number;
  content_type: string;
  processing_time_ms: number;
}
