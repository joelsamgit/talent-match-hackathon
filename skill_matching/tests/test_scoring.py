"""
test_scoring.py — Unit tests for match score math and fallback fuzzy matcher.
"""

import pytest
from scoring import calculate_match_score, fallback_match
from models import MatchConfidence, ImportanceLevel


class TestScoreMath:

    def test_all_matched_high_confidence_returns_100(self):
        """100% high confidence matches should return 100."""
        matched = [
            {"match_confidence": "high"},
            {"match_confidence": "high"},
            {"match_confidence": "high"},
        ]
        missing = []
        score = calculate_match_score(matched, missing)
        assert score == 100

    def test_zero_matched_skills_returns_0(self):
        """0 matched skills and 5 missing skills should return 0."""
        matched = []
        missing = [{"importance": "high"}] * 5
        score = calculate_match_score(matched, missing)
        assert score == 0

    def test_empty_lists_return_0(self):
        """No skills at all should return 0."""
        assert calculate_match_score([], []) == 0

    def test_weighted_confidence_calculation(self):
        """
        2 matched (1 high = 1.0, 1 medium = 0.6), 1 missing (0.0).
        Total = 3 skills (max weight 3.0).
        Score = (1.6 / 3.0) * 100 = 53.33% -> 53.
        """
        matched = [
            {"match_confidence": "high"},
            {"match_confidence": "medium"},
        ]
        missing = [{"importance": "medium"}]
        score = calculate_match_score(matched, missing)
        assert score == 53

    def test_score_clamped_between_0_and_100(self):
        """Score should never exceed 100 or drop below 0."""
        matched = [{"match_confidence": "high"}] * 10
        missing = []
        assert 0 <= calculate_match_score(matched, missing) <= 100


class TestFallbackMatch:

    def test_fallback_match_structure(self, sample_jd_analytics, sample_candidate_profile):
        """Fallback match should return valid structure matching output spec."""
        res = fallback_match(sample_jd_analytics, sample_candidate_profile)
        assert res["candidate_name"] == "Ananya Rao"
        assert res["company"] == "Google LLC"
        assert 0 <= res["match_score"] <= 100
        assert isinstance(res["matched_skills"], list)
        assert isinstance(res["missing_skills"], list)
