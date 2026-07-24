"""
test_matcher.py — Semantic Groq LLM Engine & Fallback Unit Tests for matcher.py

Coverage:
  1. Valid LLM response -> Pydantic SkillMatchingOutput model
  2. Malformed LLM response -> Graceful fallback matcher takes over
  3. LLM API exception -> Graceful fallback matcher without crashing
  4. LLM API timeout / connection error handling
  5. Missing required fields in LLM response populated with defaults
  6. Implicit skill matching (e.g. C++ scheduler -> OS / System Design)
  7. Confidence rating validation (constrained to high, medium, low)
  8. Empty candidate profile -> all skills in missing_skills
  9. Special characters & tech stacks (C++, C#, .NET, Node.js, A/B Testing)
 10. Category code normalization (hallucinated codes coerced to valid CategoryCode)
 11. Company & role extraction from JD analytics
 12. Candidate name extraction from profile
 13. High score for matching tech stack
 14. Low score for mismatched tech stack
 15. Executive summary generation
 16. Missing skills sorted by importance
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from matcher import match_skills
from models import SkillMatchingOutput, MatchConfidence, ImportanceLevel
from tests.conftest import make_mock_groq_client, MOCK_MATCH_JSON


class TestMatcherCore:

    def test_valid_llm_response_returns_pydantic_output(self, sample_jd_analytics, sample_candidate_profile):
        """Valid LLM response converts to SkillMatchingOutput model."""
        mock_client = make_mock_groq_client()
        with patch("matcher._get_client", return_value=mock_client):
            output = match_skills(sample_jd_analytics, sample_candidate_profile)

        assert isinstance(output, SkillMatchingOutput)
        assert output.candidate_name == "Ananya Rao"
        assert output.company == "Google LLC"
        assert output.role == "Software Engineer (SWE)"
        assert len(output.matched_skills) == 3
        assert len(output.missing_skills) == 1

    def test_malformed_json_triggers_fallback_matcher(self, sample_jd_analytics, sample_candidate_profile):
        """Non-JSON response from LLM falls back to fallback matcher gracefully."""
        mock_message = MagicMock()
        mock_message.content = "Malformed JSON {broken..."
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("matcher._get_client", return_value=mock_client):
            output = match_skills(sample_jd_analytics, sample_candidate_profile)

        assert isinstance(output, SkillMatchingOutput)
        assert output.candidate_name == "Ananya Rao"
        assert 0 <= output.match_score <= 100

    def test_groq_api_exception_triggers_fallback_matcher(self, sample_jd_analytics, sample_candidate_profile):
        """Groq API error (connection, timeout) falls back without crashing."""
        mock_client = make_mock_groq_client()
        mock_client.chat.completions.create.side_effect = RuntimeError("Groq Connection Error")

        with patch("matcher._get_client", return_value=mock_client):
            output = match_skills(sample_jd_analytics, sample_candidate_profile)

        assert isinstance(output, SkillMatchingOutput)
        assert 0 <= output.match_score <= 100

    def test_no_api_key_triggers_fallback_matcher(self, sample_jd_analytics, sample_candidate_profile):
        """Missing GROQ_API_KEY triggers fallback matcher cleanly."""
        with patch("matcher._get_client", side_effect=RuntimeError("GROQ_API_KEY is not set")):
            output = match_skills(sample_jd_analytics, sample_candidate_profile)

        assert isinstance(output, SkillMatchingOutput)

    def test_missing_fields_in_llm_json(self, sample_jd_analytics, sample_candidate_profile):
        """LLM response missing optional keys is assigned sensible defaults."""
        payload = {
            "matched_skills": [
                {
                    "jd_skill_name": "DSA",
                    "category_code": "DSA",
                    "candidate_skill_name": "DSA",
                }
            ],
            "missing_skills": [
                {
                    "jd_skill_name": "Cloud",
                    "category_code": "SYSD",
                }
            ]
        }
        mock_client = make_mock_groq_client(payload)
        with patch("matcher._get_client", return_value=mock_client):
            output = match_skills(sample_jd_analytics, sample_candidate_profile)

        assert output.matched_skills[0].match_confidence == MatchConfidence.HIGH
        assert output.missing_skills[0].importance == ImportanceLevel.MEDIUM

    def test_invalid_category_code_coerced_to_apti(self, sample_jd_analytics, sample_candidate_profile):
        """Hallucinated category code from LLM is coerced to APTI."""
        payload = {
            "summary": "Match",
            "matched_skills": [
                {
                    "jd_skill_name": "Problem Solving",
                    "category_code": "INVALID_CODE",
                    "candidate_skill_name": "Logic",
                    "match_confidence": "high",
                    "explanation": "Matched"
                }
            ],
            "missing_skills": []
        }
        mock_client = make_mock_groq_client(payload)
        with patch("matcher._get_client", return_value=mock_client):
            output = match_skills(sample_jd_analytics, sample_candidate_profile)

        assert output.matched_skills[0].category_code == "APTI"

    def test_empty_candidate_skills_in_payload(self, sample_jd_analytics):
        """Empty candidate skills list handles gracefully."""
        empty_profile = {"candidate_name": "NoSkill Candidate", "skills": []}
        with patch("matcher._get_client", side_effect=RuntimeError("Fallback")):
            output = match_skills(sample_jd_analytics, empty_profile)

        assert isinstance(output, SkillMatchingOutput)
        assert output.match_score == 0
        assert len(output.missing_skills) == len(sample_jd_analytics["skills"])

    def test_special_characters_in_skill_names(self):
        """Skills containing C++, C#, .NET, Node.js parse cleanly."""
        jd_analytics = {
            "company": "Tech Corp",
            "role": "Backend Engineer",
            "skills": [
                {"skill_name": "C++ & .NET Core", "category_code": "COD"},
                {"skill_name": "Node.js & REST APIs", "category_code": "NETW"},
            ]
        }
        candidate_profile = {
            "candidate_name": "Dev",
            "skills": [
                {"skill_name": "C++ Programming", "category_code": "COD"},
                {"skill_name": "Node.js REST Services", "category_code": "NETW"},
            ]
        }
        with patch("matcher._get_client", side_effect=RuntimeError("Fallback")):
            output = match_skills(jd_analytics, candidate_profile)

        assert output.match_score > 0

    def test_missing_skills_are_sorted_by_importance(self, sample_jd_analytics, sample_candidate_profile):
        """Missing skills in output are sorted high > medium > low."""
        payload = {
            "summary": "Match summary",
            "matched_skills": [],
            "missing_skills": [
                {"jd_skill_name": "LowSkill", "category_code": "COD", "importance": "low", "explanation": "gap"},
                {"jd_skill_name": "HighSkill", "category_code": "DSA", "importance": "high", "explanation": "gap"},
                {"jd_skill_name": "MedSkill", "category_code": "OS", "importance": "medium", "explanation": "gap"},
            ]
        }
        mock_client = make_mock_groq_client(payload)
        with patch("matcher._get_client", return_value=mock_client):
            output = match_skills(sample_jd_analytics, sample_candidate_profile)

        assert output.missing_skills[0].importance == ImportanceLevel.HIGH
        assert output.missing_skills[1].importance == ImportanceLevel.MEDIUM
        assert output.missing_skills[2].importance == ImportanceLevel.LOW

    def test_company_and_role_fallback_metadata(self):
        """Missing company or role defaults to sensible placeholder."""
        jd_analytics = {"source_file": "custom.pdf", "skills": []}
        candidate_profile = {"name": "Test User", "skills": []}

        with patch("matcher._get_client", side_effect=RuntimeError("Fallback")):
            output = match_skills(jd_analytics, candidate_profile)

        assert output.company == "Target Company"
        assert output.role == "Target Role"
        assert output.candidate_name == "Test User"

    def test_implicit_skill_matching_prompt_structure(self, sample_jd_analytics, sample_candidate_profile):
        """Verify LLM client receives prompt containing candidate profile and JD text."""
        mock_client = make_mock_groq_client()
        with patch("matcher._get_client", return_value=mock_client):
            match_skills(sample_jd_analytics, sample_candidate_profile)

        call_args = mock_client.chat.completions.create.call_args
        assert call_args is not None
        messages = call_args.kwargs["messages"]
        user_msg = messages[1]["content"]
        assert "Google LLC" in user_msg
        assert "Ananya Rao" in user_msg

    def test_high_match_score_for_matching_profile(self, sample_jd_analytics, sample_candidate_profile):
        """Candidate with matching skills gets high score."""
        mock_client = make_mock_groq_client()
        with patch("matcher._get_client", return_value=mock_client):
            output = match_skills(sample_jd_analytics, sample_candidate_profile)

        assert output.match_score >= 60

    def test_low_match_score_for_mismatched_profile(self, sample_jd_analytics):
        """Candidate with no overlapping skills gets low score."""
        mismatched_profile = {
            "candidate_name": "Sales Rep",
            "skills": [{"skill_name": "Cold Calling", "category_code": "COMM"}]
        }
        payload = {
            "summary": "Mismatched candidate for engineering role.",
            "matched_skills": [],
            "missing_skills": [
                {"jd_skill_name": "DSA", "category_code": "DSA", "importance": "high", "explanation": "gap"},
                {"jd_skill_name": "OS", "category_code": "OS", "importance": "high", "explanation": "gap"},
                {"jd_skill_name": "SYSD", "category_code": "SYSD", "importance": "high", "explanation": "gap"},
            ]
        }
        mock_client = make_mock_groq_client(payload)
        with patch("matcher._get_client", return_value=mock_client):
            output = match_skills(sample_jd_analytics, mismatched_profile)

        assert output.match_score == 0

    def test_summary_field_populated(self, sample_jd_analytics, sample_candidate_profile):
        """summary field in output is non-empty."""
        mock_client = make_mock_groq_client()
        with patch("matcher._get_client", return_value=mock_client):
            output = match_skills(sample_jd_analytics, sample_candidate_profile)

        assert output.summary
        assert len(output.summary) > 10

    def test_jd_source_file_preserved(self, sample_jd_analytics, sample_candidate_profile):
        """jd_source_file field in output reflects JD source file."""
        mock_client = make_mock_groq_client()
        with patch("matcher._get_client", return_value=mock_client):
            output = match_skills(sample_jd_analytics, sample_candidate_profile)

        assert output.jd_source_file == "Google LLC - Software Engineer.pdf"

    def test_invalid_confidence_level_coerced(self, sample_jd_analytics, sample_candidate_profile):
        """Invalid confidence level string defaults to high."""
        payload = {
            "summary": "Match",
            "matched_skills": [
                {
                    "jd_skill_name": "DSA",
                    "category_code": "DSA",
                    "candidate_skill_name": "DSA",
                    "match_confidence": "UNKNOWN_CONFIDENCE",
                    "explanation": "Matched"
                }
            ],
            "missing_skills": []
        }
        mock_client = make_mock_groq_client(payload)
        with patch("matcher._get_client", return_value=mock_client):
            output = match_skills(sample_jd_analytics, sample_candidate_profile)

        assert output.matched_skills[0].match_confidence == MatchConfidence.HIGH
