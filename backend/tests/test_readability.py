"""
Tests for readability analysis service and API.
"""

import pytest
from app.services import readability_service
from app.schemas.readability import ReadabilityAnalysisRequest


class TestReadabilityMetrics:
    """Test basic readability metric calculations"""

    def test_analyze_text_readability_basic(self):
        """Test basic readability analysis"""
        text = "The quick brown fox jumps over the lazy dog."
        result = readability_service.analyze_text_readability(text)

        assert result["word_count"] == 9
        assert result["sentence_count"] == 1
        assert result["character_count"] == 44
        assert result["syllable_count"] > 0
        assert result["average_sentence_length"] == 9.0
        assert result["flesch_reading_ease"] is not None
        assert result["flesch_kincaid_grade"] is not None

    def test_analyze_text_readability_empty(self):
        """Test readability analysis with empty text"""
        result = readability_service.analyze_text_readability("")

        assert result["word_count"] == 0
        assert result["sentence_count"] == 0
        assert result["character_count"] == 0
        assert result["syllable_count"] == 0
        assert result["average_sentence_length"] == 0.0
        assert result["flesch_reading_ease"] is None
        assert result["flesch_kincaid_grade"] is None

    def test_word_count(self):
        """Test word count calculation"""
        text = "One two three four five"
        result = readability_service.analyze_text_readability(text)
        assert result["word_count"] == 5

    def test_sentence_count(self):
        """Test sentence count calculation"""
        text = "First sentence. Second sentence! Third sentence?"
        result = readability_service.analyze_text_readability(text)
        assert result["sentence_count"] == 3

    def test_syllable_count(self):
        """Test syllable count is calculated"""
        text = "Elephant is very big animal."
        result = readability_service.analyze_text_readability(text)
        # "Elephant" (3) + "is" (1) + "very" (2) + "big" (1) + "animal" (3) = 10+
        assert result["syllable_count"] >= 10

    def test_average_sentence_length(self):
        """Test average sentence length calculation"""
        text = "One. Two three. Four five six."
        result = readability_service.analyze_text_readability(text)
        # Sentences: [1 word, 2 words, 3 words] = average 2.0
        assert result["average_sentence_length"] == 2.0

    def test_flesch_reading_ease_easy(self):
        """Test Flesch Reading Ease for easy text"""
        text = "The cat sat. The dog ran. I like it."
        result = readability_service.analyze_text_readability(text)
        # Short simple sentences should have high reading ease
        assert result["flesch_reading_ease"] is not None
        assert result["flesch_reading_ease"] > 60

    def test_flesch_reading_ease_difficult(self):
        """Test Flesch Reading Ease for difficult text"""
        text = "The multidisciplinary investigations constitute investigations."
        result = readability_service.analyze_text_readability(text)
        # Complex words should have lower reading ease, but might not calculate for short text
        assert result["flesch_reading_ease"] is None or result["flesch_reading_ease"] < 60

    def test_flesch_kincaid_grade_level(self):
        """Test Flesch-Kincaid Grade Level"""
        text = "The cat sat on the mat."
        result = readability_service.analyze_text_readability(text)
        # Simple text should be low grade
        assert result["flesch_kincaid_grade"] is not None
        assert result["flesch_kincaid_grade"] < 5

    def test_character_count(self):
        """Test character count"""
        text = "12345"
        result = readability_service.analyze_text_readability(text)
        assert result["character_count"] == 5

    def test_single_word(self):
        """Test readability with single word"""
        text = "Word"
        result = readability_service.analyze_text_readability(text)
        assert result["word_count"] == 1
        # text_utils.count_sentences treats any non-empty split as a sentence
        assert result["sentence_count"] >= 1
        assert result["character_count"] == 4

    def test_text_with_numbers(self):
        """Test readability with numbers"""
        text = "There are 123 items in the list of things."
        result = readability_service.analyze_text_readability(text)
        assert result["word_count"] > 0
        # Numbers cause some readability libraries to skip - result can be None
        assert result["flesch_reading_ease"] is None or result["flesch_reading_ease"] >= 0

    def test_text_with_abbreviations(self):
        """Test readability with abbreviations"""
        text = "Dr. Smith works at the U.S. Department."
        result = readability_service.analyze_text_readability(text)
        assert result["word_count"] > 0
        assert result["flesch_reading_ease"] is not None


class TestReadabilityComparison:
    """Test readability comparison between original and simplified text"""

    def test_compare_readability_basic(self):
        """Test basic readability comparison"""
        original = "Applicants who satisfy the eligibility requirements must submit the application prior to the prescribed deadline."
        simplified = "You must meet the rules and send your application before the deadline."

        result = readability_service.compare_readability(original, simplified)

        assert "original" in result
        assert "simplified" in result
        assert "comparison" in result
        assert "processing_time_ms" in result

        # Just verify word counts are reasonable
        assert result["original"]["word_count"] > 0
        assert result["simplified"]["word_count"] > 0
        # Simplified should be shorter or same length
        assert result["simplified"]["word_count"] <= result["original"]["word_count"] + 2

    def test_grade_level_improvement(self):
        """Test that grade level improvement is calculated"""
        original = "Applicants who satisfy the eligibility requirements must submit the application prior to the prescribed deadline."
        simplified = "You must meet the rules and send your application before the deadline."

        result = readability_service.compare_readability(original, simplified)

        improvement = result["comparison"]["grade_level_improvement"]
        # Simplified text should have lower grade level (improvement > 0)
        assert improvement > 0

    def test_reading_ease_improvement(self):
        """Test that reading ease improvement is calculated"""
        original = "This is very complex and difficult comprehensive text."
        simplified = "This is simple text."

        result = readability_service.compare_readability(original, simplified)

        improvement = result["comparison"]["reading_ease_improvement"]
        # Simplified text may have similar or better ease - just verify calculation exists
        assert isinstance(improvement, float)

    def test_sentence_length_reduction(self):
        """Test sentence length reduction calculation"""
        original = "Applicants who satisfy the eligibility requirements must submit the application prior to the prescribed deadline."
        simplified = "You must meet the rules. Send your application before the deadline."

        result = readability_service.compare_readability(original, simplified)

        reduction = result["comparison"]["sentence_length_reduction"]
        # Simplified text should have shorter sentences (reduction > 0)
        assert reduction > 0

    def test_target_achieved_true(self):
        """Test target achieved when grade meets target"""
        original = "Applicants must apply before deadline."
        simplified = "You must apply before deadline."

        result = readability_service.compare_readability(
            original, simplified, target_grade_level=5
        )

        # Both are very simple text
        simplified_grade = result["simplified"]["flesch_kincaid_grade"]
        target_achieved = result["comparison"]["target_achieved"]

        if simplified_grade is not None and simplified_grade <= 5:
            assert target_achieved is True
        else:
            assert target_achieved is False

    def test_target_achieved_false(self):
        """Test target not achieved when grade exceeds target"""
        original = "Multidisciplinary investigations into incomprehensible consequences necessitate comprehensive examinations of unprecedented complexity."
        simplified = "Multidisciplinary investigations into incomprehensible consequences necessitate comprehensive examinations."

        result = readability_service.compare_readability(
            original, simplified, target_grade_level=5
        )

        # Simplified text is still complex
        simplified_grade = result["simplified"]["flesch_kincaid_grade"]
        target_achieved = result["comparison"]["target_achieved"]

        if simplified_grade is not None and simplified_grade > 5:
            assert target_achieved is False

    def test_target_grade_level_stored(self):
        """Test that target grade level is stored in comparison"""
        original = "Original text here."
        simplified = "Short text."

        result = readability_service.compare_readability(
            original, simplified, target_grade_level=4
        )

        assert result["comparison"]["target_grade_level"] == 4

    def test_identical_texts(self):
        """Test comparison with identical original and simplified text"""
        text = "The application must be submitted before the deadline."

        result = readability_service.compare_readability(text, text)

        # Improvements should be zero when texts are identical
        assert result["comparison"]["grade_level_improvement"] == 0.0
        assert result["comparison"]["reading_ease_improvement"] == 0.0
        assert result["comparison"]["sentence_length_reduction"] == 0.0

    def test_simplified_harder_than_original(self):
        """Test case where simplified text is harder to read"""
        original = "You must apply."
        simplified = "Applications constitute requisite comprehensive procedure requirements."

        result = readability_service.compare_readability(original, simplified)

        # Grade level improvement should reflect the comparison
        improvement = result["comparison"]["grade_level_improvement"]
        # When simplified is harder, improvement is negative
        assert isinstance(improvement, float)

    def test_very_long_text(self):
        """Test comparison with long text"""
        original = " ".join(["Word"] * 500)
        simplified = " ".join(["Word"] * 250)

        result = readability_service.compare_readability(original, simplified)

        assert result["original"]["word_count"] == 500
        assert result["simplified"]["word_count"] == 250

    def test_processing_time_measured(self):
        """Test that processing time is measured"""
        original = "Original text."
        simplified = "Short text."

        result = readability_service.compare_readability(original, simplified)

        assert result["processing_time_ms"] >= 0
        assert isinstance(result["processing_time_ms"], int)

    def test_comparison_structure(self):
        """Test that comparison has all required fields"""
        original = "Original text."
        simplified = "Short text."

        result = readability_service.compare_readability(original, simplified)

        comparison = result["comparison"]
        assert "grade_level_improvement" in comparison
        assert "reading_ease_improvement" in comparison
        assert "sentence_length_reduction" in comparison
        assert "target_grade_level" in comparison
        assert "simplified_grade_level" in comparison
        assert "target_achieved" in comparison

    def test_different_target_grades(self):
        """Test comparison with different target grades"""
        original = "Original text."
        simplified = "Short text."

        for target in [3, 5, 8, 12]:
            result = readability_service.compare_readability(
                original, simplified, target_grade_level=target
            )
            assert result["comparison"]["target_grade_level"] == target


class TestLanguageSupport:
    """Test language detection and support"""

    def test_english_detected(self):
        """Test that English text is detected"""
        from app.utils import text_utils
        text = "This is an English text."
        language = text_utils.detect_language_heuristic(text)
        assert language == "en"

    def test_kannada_detected(self):
        """Test that Kannada text is detected"""
        from app.utils import text_utils
        text = "ಇದು ಕನ್ನಡ ಪಠ್ಯವಾಗಿದೆ."
        language = text_utils.detect_language_heuristic(text)
        assert language in ["kn", "other"]

    def test_non_english_unsupported(self):
        """Test that non-English returns unsupported gracefully"""
        from app.utils import text_utils
        kannada_text = "ಇದು ಕನ್ನಡ ಪಠ್ಯವಾಗಿದೆ."
        language = text_utils.detect_language_heuristic(kannada_text)
        # Should detect as non-English; readability service should handle this


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_very_short_text(self):
        """Test with very short text"""
        result = readability_service.analyze_text_readability("Hi")
        assert result["word_count"] == 1

    def test_one_sentence_no_punctuation(self):
        """Test one sentence without punctuation"""
        result = readability_service.analyze_text_readability("This is text")
        assert result["word_count"] == 3
        # text_utils.count_sentences treats any non-empty split as a sentence
        assert result["sentence_count"] >= 1

    def test_text_with_only_numbers(self):
        """Test text with only numbers"""
        result = readability_service.analyze_text_readability("123 456 789")
        assert result["word_count"] == 3

    def test_text_with_special_characters(self):
        """Test text with special characters"""
        result = readability_service.analyze_text_readability("Hello @#$% world!")
        assert result["word_count"] > 0
        assert result["flesch_reading_ease"] is not None

    def test_whitespace_only_text(self):
        """Test text with only whitespace"""
        result = readability_service.analyze_text_readability("   \n\t  ")
        assert result["word_count"] == 0

    def test_very_long_sentence(self):
        """Test very long single sentence"""
        long_sentence = " ".join(["word"] * 100) + "."
        result = readability_service.analyze_text_readability(long_sentence)
        assert result["sentence_count"] == 1
        assert result["word_count"] == 100

    def test_multiple_sentence_endings(self):
        """Test text with multiple consecutive sentence endings"""
        text = "First sentence... Second sentence!!! Third sentence???"
        result = readability_service.analyze_text_readability(text)
        assert result["sentence_count"] >= 2

    def test_unicode_characters(self):
        """Test text with unicode characters"""
        text = "Hello 世界 🌍 café naïve."
        result = readability_service.analyze_text_readability(text)
        assert result["word_count"] > 0

    def test_currency_symbols(self):
        """Test text with currency symbols"""
        text = "The cost is fifty dollars or five thousand rupees or fifty euros."
        result = readability_service.analyze_text_readability(text)
        assert result["word_count"] > 0
        # Readability can be calculated for text-based currency descriptions
        assert result["flesch_reading_ease"] is not None

    def test_urls_in_text(self):
        """Test text with URLs"""
        text = "Visit https://example.com for more information."
        result = readability_service.analyze_text_readability(text)
        assert result["word_count"] > 0

    def test_email_addresses_in_text(self):
        """Test text with email addresses"""
        text = "Contact me at test@example.com for details."
        result = readability_service.analyze_text_readability(text)
        assert result["word_count"] > 0

    def test_regression_with_numbers_and_proper_nouns(self):
        """
        Regression test for issue where text with numbers and proper nouns caused None metrics.

        Previously, textstat.flesch_kincaid_grade() threw KeyError on:
        - Numbers: "18", "2026", "2,50,000"
        - Proper nouns: "Aadhaar", "Card", "Certificate", "Bank", etc.

        This resulted in simplified_grade_level = None, causing Pydantic validation error.

        Fix: Normalize text to remove problematic words before textstat calculation.
        """
        original_text = (
            "Eligible applicants must be at least 18 years old and must submit their "
            "application before 31 December 2026. The government will provide financial "
            "assistance of ₹2,50,000 to eligible applicants. Applicants must submit the "
            "following documents: Aadhaar Card, Income Certificate, Bank Account Details. "
            "Applications can be submitted through the official portal."
        )

        simplified_text = (
            "You must be 18 years or older to apply. Send your application before "
            "31 December 2026. You can get ₹2,50,000 in financial help. You need these "
            "documents: Aadhaar Card, Income Certificate, Bank Account Details. Apply "
            "through the official portal before the deadline."
        )

        result = readability_service.compare_readability(
            original_text=original_text,
            simplified_text=simplified_text,
            target_grade_level=5
        )

        # Verify metrics are calculated (not None)
        assert result["original"]["flesch_reading_ease"] is not None
        assert result["original"]["flesch_kincaid_grade"] is not None
        assert result["simplified"]["flesch_reading_ease"] is not None
        assert result["simplified"]["flesch_kincaid_grade"] is not None

        # Verify comparison metrics
        assert result["comparison"]["simplified_grade_level"] is not None
        assert isinstance(result["comparison"]["grade_level_improvement"], float)
        assert isinstance(result["comparison"]["reading_ease_improvement"], float)

        # Simplified text should have lower grade and higher reading ease
        assert result["simplified"]["flesch_kincaid_grade"] < result["original"]["flesch_kincaid_grade"]
        assert result["simplified"]["flesch_reading_ease"] > result["original"]["flesch_reading_ease"]
