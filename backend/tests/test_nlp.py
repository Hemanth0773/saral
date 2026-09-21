"""
Tests for NLP preprocessing service and endpoint.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import nlp_service
from app.schemas.nlp import NLPProcessingResponse, SentenceToken, NamedEntity, KeyPhrase


# TestClient for endpoint tests
client = TestClient(app)


class TestNLPService:
    """Test cases for NLP service functions"""

    def test_normalize_text(self):
        """Test text normalization"""
        raw_text = "  Multiple   spaces  and  \n\n  newlines  "
        normalized = nlp_service.normalize_text(raw_text)
        assert normalized == "Multiple spaces and newlines"

    def test_normalize_text_empty(self):
        """Test normalization of empty text"""
        normalized = nlp_service.normalize_text("")
        assert normalized == ""

    def test_normalize_text_with_punctuation(self):
        """Test normalization preserves sentence structure"""
        text = "Hello , world . How are you ?"
        normalized = nlp_service.normalize_text(text)
        # Punctuation should be properly spaced
        assert "," in normalized or "." in normalized

    def test_preprocess_text_basic(self):
        """Test basic text preprocessing"""
        text = "The Government of India launched a new scheme. It aims to help citizens."
        result = nlp_service.preprocess_text(text)

        assert isinstance(result, NLPProcessingResponse)
        assert result.success is True
        assert result.document_id.startswith("doc_")
        assert len(result.normalized_text) > 0
        assert len(result.sentences) >= 2

    def test_preprocess_text_sentence_extraction(self):
        """Test sentence tokenization"""
        text = "First sentence. Second sentence! Third sentence?"
        result = nlp_service.preprocess_text(text)

        assert len(result.sentences) >= 3
        assert all(isinstance(s, SentenceToken) for s in result.sentences)
        assert result.sentences[0].sentence_id == 0
        assert result.sentences[1].sentence_id == 1

    def test_preprocess_text_entity_extraction(self):
        """Test named entity recognition"""
        text = "John Smith works at Google in New York."
        result = nlp_service.preprocess_text(text)

        # Should extract some entities
        assert len(result.entities) > 0
        assert all(isinstance(e, NamedEntity) for e in result.entities)

        # Check for expected entity types
        entity_labels = [e.label for e in result.entities]
        assert any(label in entity_labels for label in ["PERSON", "ORG", "GPE"])

    def test_preprocess_text_pos_tags(self):
        """Test part-of-speech tagging"""
        text = "The quick brown fox jumps."
        result = nlp_service.preprocess_text(text)

        assert len(result.pos_tags) > 0
        # Should have determiners, adjectives, nouns, verbs
        pos_tags = [tag.pos for tag in result.pos_tags]
        assert any(pos in pos_tags for pos in ["DET", "ADJ", "NOUN", "VERB"])

    def test_preprocess_text_key_phrases(self):
        """Test key phrase extraction"""
        text = "Housing assistance scheme provides affordable housing solutions. The scheme includes housing credits."
        result = nlp_service.preprocess_text(text)

        assert len(result.key_phrases) > 0
        assert all(isinstance(p, KeyPhrase) for p in result.key_phrases)

        # "housing" related phrases should be extracted
        phrase_texts = [p.text.lower() for p in result.key_phrases]
        assert any("housing" in phrase for phrase in phrase_texts)

    def test_preprocess_text_metadata(self):
        """Test processing metadata"""
        text = "Sample text for processing."
        result = nlp_service.preprocess_text(text)

        metadata = result.processing_metadata
        assert metadata.model_used == "en_core_web_sm"
        assert metadata.processing_time_ms >= 0
        assert metadata.language_detected in ["en", "kn", "hi", "ta", "te", "ml", "other"]
        assert "Z" in metadata.timestamp  # ISO 8601 format

    def test_preprocess_text_empty_raises_error(self):
        """Test that empty text raises ValueError"""
        with pytest.raises(ValueError, match="cannot be empty"):
            nlp_service.preprocess_text("")

    def test_preprocess_text_whitespace_only_raises_error(self):
        """Test that whitespace-only text raises ValueError"""
        with pytest.raises(ValueError, match="cannot be empty"):
            nlp_service.preprocess_text("   \n\t  ")

    def test_preprocess_text_with_document_id(self):
        """Test preprocessing with custom document ID"""
        text = "Sample text."
        custom_id = "custom_doc_12345"
        result = nlp_service.preprocess_text(text, document_id=custom_id)

        assert result.document_id == custom_id

    def test_extract_sentences_returns_list(self):
        """Test that extract_sentences returns a list of SentenceToken"""
        nlp = nlp_service._load_spacy_model()
        text = "First sentence. Second sentence."
        doc = nlp(text)

        sentences = nlp_service.extract_sentences(doc)
        assert isinstance(sentences, list)
        assert len(sentences) >= 2
        assert all(isinstance(s, SentenceToken) for s in sentences)

    def test_extract_entities_returns_list(self):
        """Test that extract_entities returns a list of NamedEntity"""
        nlp = nlp_service._load_spacy_model()
        text = "Apple is in California."
        doc = nlp(text)

        entities = nlp_service.extract_entities(doc)
        assert isinstance(entities, list)
        assert all(isinstance(e, NamedEntity) for e in entities)

    def test_extract_pos_tags_returns_list(self):
        """Test that extract_pos_tags returns a list of POSTag"""
        nlp = nlp_service._load_spacy_model()
        text = "The cat sat."
        doc = nlp(text)

        pos_tags = nlp_service.extract_pos_tags(doc)
        assert isinstance(pos_tags, list)
        assert len(pos_tags) == 4  # 4 tokens
        assert all(hasattr(tag, "pos") for tag in pos_tags)

    def test_analyze_text_readability(self):
        """Test readability analysis"""
        text = "This is a test. Another sentence."
        metrics = nlp_service.analyze_text_readability(text)

        assert "word_count" in metrics
        assert "sentence_count" in metrics
        assert "character_count" in metrics
        assert "estimated_reading_time_minutes" in metrics
        assert "avg_word_length" in metrics
        assert "avg_sentence_length" in metrics

    def test_model_caching(self):
        """Test that spaCy model is cached after first load"""
        model1 = nlp_service._load_spacy_model()
        model2 = nlp_service._load_spacy_model()

        # Should be the same object (cached)
        assert model1 is model2


class TestNLPEndpoint:
    """Test cases for the NLP preprocessing endpoint"""

    def test_preprocess_endpoint_success(self):
        """Test successful preprocessing endpoint"""
        response = client.post(
            "/api/documents/preprocess",
            json={"text": "Government scheme for housing assistance."}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "document_id" in data
        assert "normalized_text" in data
        assert "sentences" in data

    def test_preprocess_endpoint_empty_text(self):
        """Test preprocessing endpoint with empty text"""
        response = client.post(
            "/api/documents/preprocess",
            json={"text": ""}
        )

        # Empty string fails Pydantic validation (min_length=1)
        assert response.status_code == 422

    def test_preprocess_endpoint_whitespace_only(self):
        """Test preprocessing endpoint with whitespace-only text"""
        response = client.post(
            "/api/documents/preprocess",
            json={"text": "   \n\t  "}
        )

        assert response.status_code == 400

    def test_preprocess_endpoint_missing_text_field(self):
        """Test preprocessing endpoint without text field"""
        response = client.post(
            "/api/documents/preprocess",
            json={}
        )

        assert response.status_code == 422  # Validation error

    def test_preprocess_endpoint_response_format(self):
        """Test preprocessing endpoint response format"""
        response = client.post(
            "/api/documents/preprocess",
            json={"text": "The quick brown fox jumps over the lazy dog."}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "success" in data
        assert "document_id" in data
        assert "normalized_text" in data
        assert "sentences" in data
        assert "entities" in data
        assert "pos_tags" in data
        assert "key_phrases" in data
        assert "processing_metadata" in data

        # Verify metadata
        metadata = data["processing_metadata"]
        assert "model_used" in metadata
        assert "processing_time_ms" in metadata
        assert "language_detected" in metadata
        assert "timestamp" in metadata

    def test_preprocess_endpoint_sentences_with_indices(self):
        """Test that sentences have proper positional information"""
        text = "First sentence. Second sentence."
        response = client.post(
            "/api/documents/preprocess",
            json={"text": text}
        )

        assert response.status_code == 200
        data = response.json()

        sentences = data["sentences"]
        assert len(sentences) >= 2

        for sent in sentences:
            assert "text" in sent
            assert "start_index" in sent
            assert "end_index" in sent
            assert "sentence_id" in sent
            assert sent["start_index"] >= 0
            assert sent["end_index"] > sent["start_index"]

    def test_preprocess_endpoint_entities_with_labels(self):
        """Test that entities have labels and confidence scores"""
        response = client.post(
            "/api/documents/preprocess",
            json={"text": "John works at Apple in California."}
        )

        assert response.status_code == 200
        data = response.json()

        if len(data["entities"]) > 0:
            entity = data["entities"][0]
            assert "text" in entity
            assert "label" in entity
            assert "start_index" in entity
            assert "end_index" in entity
            assert "confidence" in entity
            assert 0.0 <= entity["confidence"] <= 1.0

    def test_preprocess_endpoint_key_phrases_sorted(self):
        """Test that key phrases are sorted by relevance"""
        response = client.post(
            "/api/documents/preprocess",
            json={
                "text": "Housing scheme provides housing assistance. The housing program aims for housing solutions."
            }
        )

        assert response.status_code == 200
        data = response.json()

        key_phrases = data["key_phrases"]
        if len(key_phrases) > 1:
            # Should be sorted by score descending
            scores = [p["score"] for p in key_phrases]
            assert scores == sorted(scores, reverse=True)
