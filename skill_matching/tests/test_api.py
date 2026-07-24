"""
test_api.py — Integration tests for FastAPI endpoints in main.py.
"""

import pytest


class TestHealthEndpoint:

    def test_health_returns_200(self, test_client):
        res = test_client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"
        assert res.json()["service"] == "skill_matching"


class TestSamplesEndpoint:

    def test_samples_returns_lists(self, test_client):
        res = test_client.get("/samples")
        assert res.status_code == 200
        body = res.json()
        assert "sample_jds" in body
        assert "sample_candidates" in body
        assert "Ananya Rao" in body["sample_candidates"]


class TestMatchEndpoint:

    def test_match_post_returns_200_and_schema(self, test_client, sample_jd_analytics, sample_candidate_profile):
        payload = {
            "jd_analytics": sample_jd_analytics,
            "candidate_profile": sample_candidate_profile,
        }
        res = test_client.post("/match", json=payload)
        assert res.status_code == 200
        body = res.json()
        assert body["candidate_name"] == "Ananya Rao"
        assert body["company"] == "Google LLC"
        assert "match_score" in body
        assert "matched_skills" in body
        assert "missing_skills" in body

    def test_match_empty_body_returns_422(self, test_client):
        res = test_client.post("/match", json={})
        assert res.status_code == 422


class TestMatchSampleEndpoint:

    def test_match_sample_returns_200(self, test_client):
        payload = {
            "jd_filename": "Google LLC - Software Engineer.pdf",
            "candidate_name": "Ananya Rao"
        }
        res = test_client.post("/match-sample", json=payload)
        assert res.status_code == 200
        body = res.json()
        assert body["candidate_name"] == "Ananya Rao"
        assert 0 <= body["match_score"] <= 100
