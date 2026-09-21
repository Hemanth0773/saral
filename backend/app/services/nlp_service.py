"""
NLP processing service.
Handles text preprocessing, tokenization, entity recognition, and linguistic analysis.
"""

import time
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import spacy
from spacy.language import Language
from app.core.logging import get_logger
from app.utils import text_utils
from app.schemas.nlp import (
    NLPProcessingResponse,
    SentenceToken,
    NamedEntity,
    POSTag,
    KeyPhrase,
    NLPProcessingMetadata,
)

logger = get_logger(__name__)

# Global spaCy model cache
_nlp_model: Optional[Language] = None


def _load_spacy_model(model_name: str = "en_core_web_sm") -> Language:
    """
    Load spaCy model with caching.

    Args:
        model_name: Name of the spaCy model to load

    Returns:
        Loaded spaCy language model

    Raises:
        ValueError: If model cannot be loaded
    """
    global _nlp_model

    if _nlp_model is not None:
        return _nlp_model

    try:
        logger.info(f"Loading spaCy model: {model_name}")
        _nlp_model = spacy.load(model_name)
        logger.info(f"spaCy model loaded successfully: {model_name}")
        return _nlp_model
    except OSError as e:
        logger.error(f"Failed to load spaCy model {model_name}: {str(e)}")
        raise ValueError(
            f"NLP model '{model_name}' not found. "
            "Please install it using: python -m spacy download en_core_web_sm"
        )
    except Exception as e:
        logger.error(f"Error loading spaCy model: {str(e)}")
        raise ValueError(f"Failed to load NLP model: {str(e)}")


def normalize_text(text: str) -> str:
    """
    Normalize and clean text for NLP processing.

    Args:
        text: Raw text to normalize

    Returns:
        Normalized text
    """
    if not text:
        return ""

    # Use existing text cleaning utility
    normalized = text_utils.clean_text(text)

    # Additional normalization for NLP
    # Remove extra spaces around punctuation
    normalized = re.sub(r'\s+([.!?,;:])', r'\1', normalized)

    return normalized


def extract_sentences(nlp_doc) -> List[SentenceToken]:
    """
    Extract sentences from spaCy document.

    Args:
        nlp_doc: Processed spaCy document

    Returns:
        List of SentenceToken objects
    """
    sentences = []
    for sent_id, sent in enumerate(nlp_doc.sents):
        sentence = SentenceToken(
            text=sent.text,
            start_index=sent.start_char,
            end_index=sent.end_char,
            sentence_id=sent_id,
        )
        sentences.append(sentence)

    return sentences


def extract_entities(nlp_doc) -> List[NamedEntity]:
    """
    Extract named entities from spaCy document.

    Args:
        nlp_doc: Processed spaCy document

    Returns:
        List of NamedEntity objects
    """
    entities = []
    for ent in nlp_doc.ents:
        entity = NamedEntity(
            text=ent.text,
            label=ent.label_,
            start_index=ent.start_char,
            end_index=ent.end_char,
            confidence=0.90,  # spaCy doesn't provide confidence scores directly
        )
        entities.append(entity)

    return entities


def extract_pos_tags(nlp_doc) -> List[POSTag]:
    """
    Extract part-of-speech tags from spaCy document.

    Args:
        nlp_doc: Processed spaCy document

    Returns:
        List of POSTag objects
    """
    pos_tags = []
    for token_id, token in enumerate(nlp_doc):
        pos_tag = POSTag(
            text=token.text,
            pos=token.pos_,
            tag=token.tag_,
            index=token_id,
        )
        pos_tags.append(pos_tag)

    return pos_tags


def extract_key_phrases(nlp_doc, text: str) -> List[KeyPhrase]:
    """
    Extract key phrases from text using noun chunks and term frequency.

    Args:
        nlp_doc: Processed spaCy document
        text: Original text for phrase counting

    Returns:
        List of KeyPhrase objects sorted by score
    """
    phrases = {}

    # Extract noun chunks (base noun phrases)
    for chunk in nlp_doc.noun_chunks:
        phrase_text = chunk.text.lower().strip()
        if len(phrase_text) > 2:  # Skip very short phrases
            if phrase_text not in phrases:
                phrases[phrase_text] = {"count": 0, "score": 0.0}
            phrases[phrase_text]["count"] += 1

    # Calculate phrase scores (TF-IDF style)
    text_lower = text.lower()
    total_phrases = len(phrases)

    for phrase_text, phrase_data in phrases.items():
        # Base score from frequency
        freq_score = phrase_data["count"] / max(1, total_phrases)

        # Boost score for longer phrases (more specific)
        length_boost = len(phrase_text.split()) / 5.0

        # Combine scores
        total_score = (freq_score * 0.7) + (length_boost * 0.3)
        phrases[phrase_text]["score"] = min(total_score, 1.0)

    # Convert to KeyPhrase objects and sort by score
    key_phrases = [
        KeyPhrase(text=phrase, score=data["score"], count=data["count"])
        for phrase, data in phrases.items()
    ]

    # Sort by score descending, then by count descending
    key_phrases.sort(key=lambda x: (x.score, x.count), reverse=True)

    # Return top phrases (limit to 20)
    return key_phrases[:20]


def preprocess_text(
    text: str, document_id: Optional[str] = None, model_name: str = "en_core_web_sm"
) -> NLPProcessingResponse:
    """
    Perform comprehensive NLP preprocessing on text.

    Args:
        text: Text to preprocess
        document_id: Optional document ID for tracking
        model_name: Name of spaCy model to use

    Returns:
        NLPProcessingResponse with linguistic analysis

    Raises:
        ValueError: If text is empty or processing fails
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

    start_time = time.time()

    try:
        # Load model
        nlp = _load_spacy_model(model_name)

        # Normalize text
        normalized_text = normalize_text(text)

        # Process with spaCy
        logger.debug(f"Processing text with spaCy ({len(normalized_text)} chars)")
        nlp_doc = nlp(normalized_text)

        # Extract linguistic features
        sentences = extract_sentences(nlp_doc)
        entities = extract_entities(nlp_doc)
        pos_tags = extract_pos_tags(nlp_doc)
        key_phrases = extract_key_phrases(nlp_doc, text)

        processing_time_ms = int((time.time() - start_time) * 1000)

        # Generate or use provided document ID
        if not document_id:
            from app.services.document_service import generate_document_id
            document_id = generate_document_id()

        # Detect language
        language = text_utils.detect_language_heuristic(text)

        # Create response
        response = NLPProcessingResponse(
            success=True,
            document_id=document_id,
            normalized_text=normalized_text,
            sentences=sentences,
            entities=entities,
            pos_tags=pos_tags,
            key_phrases=key_phrases,
            processing_metadata=NLPProcessingMetadata(
                model_used=model_name,
                processing_time_ms=processing_time_ms,
                language_detected=language,
                timestamp=datetime.utcnow().isoformat() + "Z",
            ),
        )

        logger.info(
            f"NLP preprocessing completed: {document_id} "
            f"({len(sentences)} sentences, {len(entities)} entities, "
            f"{len(key_phrases)} key phrases in {processing_time_ms}ms)"
        )

        return response

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"NLP preprocessing failed: {str(e)}")
        raise ValueError(f"Text preprocessing failed: {str(e)}")


def analyze_text_readability(text: str) -> Dict[str, Any]:
    """
    Analyze text readability metrics.

    Args:
        text: Text to analyze

    Returns:
        Dictionary with readability metrics
    """
    return {
        "word_count": text_utils.count_words(text),
        "sentence_count": text_utils.count_sentences(text),
        "character_count": len(text),
        "estimated_reading_time_minutes": text_utils.estimate_reading_time(text),
        "avg_word_length": (
            text_utils.count_words(text) / len(text)
            if len(text) > 0
            else 0
        ),
        "avg_sentence_length": (
            text_utils.count_words(text) / max(1, text_utils.count_sentences(text))
        ),
    }
