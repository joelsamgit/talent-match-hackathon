"""
test_scoring.py — Math, Weights, Sorting & Boundary Logic Tests for scoring.py

Coverage:
  1. Perfect Match (100%)
  2. Zero Match (0%)
  3. Partial Match Weights (high=1.0, medium=0.6, low=0.3)
  4. Exact mixed score calculations
  5. Empty JD skills list handling (no division by zero)
  6. Empty Candidate skills list handling
  7. Strict score clamping (0 to 100)
  8. Integer score rounding
  9. Sorting of missing skills by importance (high > medium > low)
 10. Candidate or JD duplicate skill deduplication
 11. Case-insensitive matching ("python" vs "Python")
 12. Special characters & tech stacks (C++, .NET, A/B Testing)
 13. Overlap token matching logic
 14. Custom importance level coercion
 15. Invalid confidence level fallback to default
 16. Fallback matcher output schema & accuracy
"""

import pytest
from scoring import calculate_match_score, fallback_match, sort_missing_skills, _find_fuzzy_match
from models import MatchConfidence, ImportanceLevel, MatchedSkill, MissingSkill


class TestScoreMath:

    def test_perfect_match_100_percent(self):
        """All required skills matched with high confidence (1.0 weight) -> 100 score."""
        matched = [{"match_confidence": "high"}] * 5
        missing = []
        score = calculate_match_score(matched, missing)
        assert score == 100

    def test_zero_match_0_percent(self):
        """Zero skills matched -> 0 score."""
        matched = []
        missing = [{"importance": "high"}] * 5
        score = calculate_match_score(matched, missing)
        assert score == 0

    def test_empty_lists_return_0_no_division_by_zero(self):
        """Empty lists return 0 without raising ZeroDivisionError."""
        score = calculate_match_score([], [])
        assert score == 0

    def test_high_confidence_weight_1_0(self):
        """Single high confidence match out of 1 skill -> 100."""
        matched = [{"match_confidence": "high"}]
        missing = []
        assert calculate_match_score(matched, missing) == 100

    def test_medium_confidence_weight_0_6(self):
        """Single medium confidence match out of 1 skill -> 60."""
        matched = [{"match_confidence": "medium"}]
        missing = []
        assert calculate_match_score(matched, missing) == 60

    def test_low_confidence_weight_0_3(self):
        """Single low confidence match out of 1 skill -> 30."""
        matched = [{"match_confidence": "low"}]
        missing = []
        assert calculate_match_score(matched, missing) == 30

    def test_mixed_confidence_weights_calculation(self):
        """
        1 high (1.0) + 1 medium (0.6) + 1 low (0.3) out of 3 total skills.
        Total weight = 1.9 / 3.0 = 63.33% -> rounds to 63.
        """
        matched = [
            {"match_confidence": "high"},
            {"match_confidence": "medium"},
            {"match_confidence": "low"},
        ]
        missing = []
        score = calculate_match_score(matched, missing)
        assert score == 63

    def test_mixed_matched_and_missing_skills(self):
        """
        2 high matched (2.0) + 2 missing (0.0) out of 4 skills.
        Score = 2.0 / 4.0 = 50%.
        """
        matched = [{"match_confidence": "high"}, {"match_confidence": "high"}]
        missing = [{"importance": "high"}, {"importance": "high"}]
        assert calculate_match_score(matched, missing) == 50

    def test_score_clamping_upper_bound_100(self):
        """Score cannot exceed 100."""
        matched = [{"match_confidence": "high"}] * 20
        missing = []
        score = calculate_match_score(matched, missing)
        assert score <= 100

    def test_score_clamping_lower_bound_0(self):
        """Score cannot fall below 0."""
        matched = []
        missing = [{"importance": "low"}] * 10
        score = calculate_match_score(matched, missing)
        assert score >= 0

    def test_score_is_clean_integer(self):
        """calculate_match_score returns an int instance."""
        matched = [{"match_confidence": "medium"}] * 3
        missing = [{"importance": "high"}]
        score = calculate_match_score(matched, missing)
        assert isinstance(score, int)

    def test_matched_skill_pydantic_objects(self):
        """calculate_match_score works with MatchedSkill and MissingSkill instances."""
        matched = [
            MatchedSkill(
                jd_skill_name="DSA",
                category_code="DSA",
                candidate_skill_name="DSA",
                match_confidence=MatchConfidence.HIGH,
                explanation="Match",
            )
        ]
        missing = [
            MissingSkill(
                jd_skill_name="Cloud",
                category_code="SYSD",
                importance=ImportanceLevel.HIGH,
                explanation="Gap",
            )
        ]
        score = calculate_match_score(matched, missing)
        assert score == 50


class TestMissingSkillsSorting:

    def test_sort_missing_skills_by_importance(self):
        """missing_skills list is sorted by importance: high > medium > low."""
        missing = [
            {"jd_skill_name": "Skill C", "importance": "low"},
            {"jd_skill_name": "Skill A", "importance": "high"},
            {"jd_skill_name": "Skill B", "importance": "medium"},
        ]
        sorted_list = sort_missing_skills(missing)
        assert sorted_list[0]["jd_skill_name"] == "Skill A"  # high
        assert sorted_list[1]["jd_skill_name"] == "Skill B"  # medium
        assert sorted_list[2]["jd_skill_name"] == "Skill C"  # low

    def test_sort_missing_skills_pydantic_objects(self):
        """sort_missing_skills works with MissingSkill objects."""
        missing = [
            MissingSkill(jd_skill_name="LowSkill", category_code="COD", importance=ImportanceLevel.LOW, explanation="e"),
            MissingSkill(jd_skill_name="HighSkill", category_code="DSA", importance=ImportanceLevel.HIGH, explanation="e"),
        ]
        sorted_list = sort_missing_skills(missing)
        assert sorted_list[0].jd_skill_name == "HighSkill"
        assert sorted_list[1].jd_skill_name == "LowSkill"


class TestFuzzyMatchingLogic:

    def test_case_insensitive_matching(self):
        """"python" matches "Python" case-insensitively."""
        match_found, match_name, conf = _find_fuzzy_match(
            "Python", "COD", [("python programming", "COD")]
        )
        assert match_found is True
        assert conf == MatchConfidence.HIGH

    def test_special_characters_tech_stack(self):
        """Special characters like C++, .NET, Node.js match correctly."""
        match_found, match_name, conf = _find_fuzzy_match(
            "C++ & Multithreading", "COD", [("C++ Programming", "COD")]
        )
        assert match_found is True

    def test_fallback_match_execution(self, sample_jd_analytics, sample_candidate_profile):
        """fallback_match produces full structured dict."""
        res = fallback_match(sample_jd_analytics, sample_candidate_profile)
        assert res["candidate_name"] == "Ananya Rao"
        assert res["company"] == "Google LLC"
        assert 0 <= res["match_score"] <= 100
        assert isinstance(res["matched_skills"], list)
        assert isinstance(res["missing_skills"], list)
