"""
conftest.py — Shared pytest fixtures for Skill Matching (Role 5).
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


MOCK_MATCH_JSON = {
    "summary": "Strong candidate for backend/systems engineering with excellent DSA and System Design foundation.",
    "matched_skills": [
        {
            "jd_skill_name": "Data Structures & Algorithms",
            "category_code": "DSA",
            "candidate_skill_name": "Data Structures & Algorithms (350+ competitive programming problems)",
            "match_confidence": "high",
            "explanation": "Candidate has extensive competitive programming practice in DSA."
        },
        {
            "jd_skill_name": "Operating System Fundamentals",
            "category_code": "OS",
            "candidate_skill_name": "Linux Multithreading & Process Management",
            "match_confidence": "high",
            "explanation": "Direct experience with OS concepts."
        },
        {
            "jd_skill_name": "System Design at Scale",
            "category_code": "SYSD",
            "candidate_skill_name": "Distributed Cache in C++",
            "match_confidence": "medium",
            "explanation": "Built distributed system component."
        }
    ],
    "missing_skills": [
        {
            "jd_skill_name": "Cloud Infrastructure",
            "category_code": "SYSD",
            "importance": "medium",
            "explanation": "No formal AWS/GCP/Azure experience listed on candidate profile."
        }
    ]
}


def make_mock_groq_client(json_payload: dict | None = None) -> MagicMock:
    payload = json_payload or MOCK_MATCH_JSON

    mock_message = MagicMock()
    mock_message.content = json.dumps(payload)

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    return mock_client


@pytest.fixture()
def mock_groq_client():
    return make_mock_groq_client()


@pytest.fixture()
def sample_jd_analytics():
    return {
        "source_type": "jd",
        "source_file": "Google LLC - Software Engineer.pdf",
        "company": "Google LLC",
        "role": "Software Engineer (SWE)",
        "skills": [
            {"skill_name": "Data Structures & Algorithms", "category_code": "DSA"},
            {"skill_name": "Operating System Fundamentals", "category_code": "OS"},
            {"skill_name": "System Design at Scale", "category_code": "SYSD"},
            {"skill_name": "Cloud Infrastructure", "category_code": "SYSD"},
        ],
    }


@pytest.fixture()
def sample_candidate_profile():
    return {
        "candidate_name": "Ananya Rao",
        "skills": [
            {"skill_name": "Data Structures & Algorithms", "category_code": "DSA"},
            {"skill_name": "Linux Multithreading", "category_code": "OS"},
            {"skill_name": "Distributed Systems C++", "category_code": "SYSD"},
        ],
    }


@pytest.fixture()
def test_client(monkeypatch):
    import matcher
    monkeypatch.setattr(matcher, "_get_client", lambda: make_mock_groq_client())

    from fastapi.testclient import TestClient
    from main import app

    return TestClient(app)
