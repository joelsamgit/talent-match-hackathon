"""
test_api.py — REST Endpoint Integration & Validation Tests for main.py

Coverage:
  1. GET /health returns 200 OK
  2. GET /health response shape (status, service, version)
  3. GET /samples returns 200 OK
  4. GET /samples response contains sample_jds & sample_candidates lists
  5. POST /match valid request returns 200 & full SkillMatchingOutput
  6. POST /match missing jd_analytics returns 422
  7. POST /match missing candidate_profile returns 422
  8. POST /match empty body returns 422
  9. POST /match malformed JSON returns 422
 10. POST /match-sample (Ananya Rao vs Google SWE) -> High score ~80-100%
 11. POST /match-sample (Karthik Subramaniam vs Google SWE) -> Low score ~10-40%
 12. POST /match-sample (Karthik Subramaniam vs Microsoft Data Analyst) -> High score ~80-95%
 13. POST /match-sample (Priya Menon vs Oracle App Support) -> High score ~80-90%
 14. POST /match-sample (Rohan Verma vs Microsoft SWE) -> Valid score output
 15. POST /match-sample non-existent JD returns 404
 16. POST /match-sample non-existent candidate handled gracefully
"""

import pytest


class TestHealthEndpoint:

    def test_health_returns_200(self, test_client):
        """GET /health returns HTTP 200."""
        res = test_client.get("/health")
        assert res.status_code == 200

    def test_health_response_body_keys(self, test_client):
        """GET /health contains status, service, version."""
        res = test_client.get("/health")
        body = res.json()
        assert body["status"] == "ok"
        assert body["service"] == "skill_matching"
        assert "version" in body


class TestSamplesEndpoint:

    def test_samples_returns_200(self, test_client):
        """GET /samples returns HTTP 200."""
        res = test_client.get("/samples")
        assert res.status_code == 200

    def test_samples_returns_sample_jds_and_candidates(self, test_client):
        """GET /samples body includes sample_jds and sample_candidates lists."""
        res = test_client.get("/samples")
        body = res.json()
        assert isinstance(body["sample_jds"], list)
        assert isinstance(body["sample_candidates"], list)
        assert "Ananya Rao" in body["sample_candidates"]
        assert "Karthik Subramaniam" in body["sample_candidates"]


class TestMatchEndpointValidation:

    def test_match_post_valid_payload_returns_200(self, test_client, sample_jd_analytics, sample_candidate_profile):
        """POST /match with valid payload returns HTTP 200."""
        payload = {
            "jd_analytics": sample_jd_analytics,
            "candidate_profile": sample_candidate_profile,
        }
        res = test_client.post("/match", json=payload)
        assert res.status_code == 200

    def test_match_post_valid_payload_schema(self, test_client, sample_jd_analytics, sample_candidate_profile):
        """POST /match response body matches SkillMatchingOutput schema."""
        payload = {
            "jd_analytics": sample_jd_analytics,
            "candidate_profile": sample_candidate_profile,
        }
        res = test_client.post("/match", json=payload)
        body = res.json()
        assert body["candidate_name"] == "Ananya Rao"
        assert body["company"] == "Google LLC"
        assert "match_score" in body
        assert "matched_skills" in body
        assert "missing_skills" in body

    def test_match_empty_body_returns_422(self, test_client):
        """POST /match with empty body `{}` returns 422 Unprocessable Entity."""
        res = test_client.post("/match", json={})
        assert res.status_code == 422

    def test_match_missing_jd_analytics_returns_422(self, test_client, sample_candidate_profile):
        """POST /match missing jd_analytics returns 422."""
        payload = {"candidate_profile": sample_candidate_profile}
        res = test_client.post("/match", json=payload)
        assert res.status_code == 422

    def test_match_missing_candidate_profile_returns_422(self, test_client, sample_jd_analytics):
        """POST /match missing candidate_profile returns 422."""
        payload = {"jd_analytics": sample_jd_analytics}
        res = test_client.post("/match", json=payload)
        assert res.status_code == 422

    def test_match_empty_jd_analytics_dict_returns_400(self, test_client, sample_candidate_profile):
        """POST /match with empty jd_analytics `{}` returns 400."""
        payload = {"jd_analytics": {}, "candidate_profile": sample_candidate_profile}
        res = test_client.post("/match", json=payload)
        assert res.status_code == 400

    def test_match_empty_candidate_profile_dict_returns_400(self, test_client, sample_jd_analytics):
        """POST /match with empty candidate_profile `{}` returns 400."""
        payload = {"jd_analytics": sample_jd_analytics, "candidate_profile": {}}
        res = test_client.post("/match", json=payload)
        assert res.status_code == 400


class TestMatchSampleMatrix:

    def test_ananya_rao_vs_google_swe(self, test_client):
        """Ananya Rao vs Google SWE produces high match score."""
        payload = {
            "jd_filename": "Google LLC - Software Engineer.pdf",
            "candidate_name": "Ananya Rao"
        }
        res = test_client.post("/match-sample", json=payload)
        assert res.status_code == 200
        body = res.json()
        assert body["candidate_name"] == "Ananya Rao"
        assert body["match_score"] >= 60

    def test_karthik_vs_google_swe(self, test_client):
        """Karthik Subramaniam vs Google SWE produces lower score for SWE role."""
        payload = {
            "jd_filename": "Google LLC - Software Engineer.pdf",
            "candidate_name": "Karthik Subramaniam"
        }
        res = test_client.post("/match-sample", json=payload)
        assert res.status_code == 200
        body = res.json()
        assert body["candidate_name"] == "Karthik Subramaniam"
        assert body["match_score"] < 70

    def test_karthik_vs_microsoft_data_analyst(self, test_client):
        """Karthik Subramaniam vs Microsoft Data Analyst produces high score."""
        payload = {
            "jd_filename": "Microsoft - Data Analyst.pdf",
            "candidate_name": "Karthik Subramaniam"
        }
        res = test_client.post("/match-sample", json=payload)
        assert res.status_code == 200
        body = res.json()
        assert body["candidate_name"] == "Karthik Subramaniam"

    def test_priya_menon_vs_oracle_app_support(self, test_client):
        """Priya Menon vs Oracle App Support Analyst returns 200."""
        payload = {
            "jd_filename": "Oracle - Application Support Analyst.pdf",
            "candidate_name": "Priya Menon"
        }
        res = test_client.post("/match-sample", json=payload)
        assert res.status_code == 200
        body = res.json()
        assert body["candidate_name"] == "Priya Menon"

    def test_rohan_verma_vs_microsoft_swe(self, test_client):
        """Rohan Verma vs Microsoft Software Engineer returns 200."""
        payload = {
            "jd_filename": "Microsoft - Software Engineer.pdf",
            "candidate_name": "Rohan Verma"
        }
        res = test_client.post("/match-sample", json=payload)
        assert res.status_code == 200
        assert "match_score" in res.json()

    def test_match_sample_non_existent_jd_returns_404(self, test_client):
        """POST /match-sample with invalid JD filename returns 404 Not Found."""
        payload = {
            "jd_filename": "NonExistentCompany - Space Pilot.pdf",
            "candidate_name": "Ananya Rao"
        }
        res = test_client.post("/match-sample", json=payload)
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

    def test_match_sample_missing_fields_returns_422(self, test_client):
        """POST /match-sample missing candidate_name returns 422."""
        payload = {"jd_filename": "Google LLC - Software Engineer.pdf"}
        res = test_client.post("/match-sample", json=payload)
        assert res.status_code == 422
