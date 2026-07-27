"""
test_end_to_end.py — Verification script for the 5-step integration flow.

Executes the full end-to-end pipeline against real test sample data:
  Step 1: run_jd_analytics("JD Analytics/tests/fixtures/sample_jd.txt")
  Step 2: run_resume_parsing("resume_pars/tests/sample_resume.docx")
  Step 3: Save Candidate Profile (Profile Builder backend)
  Step 4: run_talent_check(profile, "Google")
  Step 5: run_skill_match(profile, jd_output)

Prints full raw outputs at each step.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Setup paths
_INTEGRATION_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _INTEGRATION_DIR.parent
_PROFILE_BUILDER_DIR = _REPO_ROOT / "profile_builder" / "backend"

for d in (_INTEGRATION_DIR, _REPO_ROOT, _PROFILE_BUILDER_DIR):
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))

from orchestrator import (
    run_jd_analytics,
    run_resume_parsing,
    run_talent_check,
    run_skill_match,
)
from profile_builder.backend.main import save_profile, Profile as ProfileModel, Skill as ProfileSkill


def main():
    print("=" * 70)
    print("RADIX TALENT MATCH — END-TO-END INTEGRATION TEST")
    print("=" * 70)

    # File paths
    repo_root = _INTEGRATION_DIR.parent
    jd_path = repo_root / "JD Analytics" / "tests" / "fixtures" / "sample_jd.txt"
    resume_path = repo_root / "resume_pars" / "tests" / "sample_resume.docx"

    # -----------------------------------------------------------------------
    # Step 1: JD Analytics
    # -----------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("STEP 1: JD Analytics (run_jd_analytics)")
    print("-" * 70)
    jd_output = run_jd_analytics(str(jd_path))
    print(json.dumps(jd_output, indent=2))
    assert jd_output.get("source_type") == "jd", "Step 1 failed: source_type != 'jd'"
    assert len(jd_output.get("skills", [])) > 0, "Step 1 failed: skills list is empty"
    print(f"\n[PASSED] STEP 1 PASSED: Extracted {len(jd_output['skills'])} skills from JD.")

    # -----------------------------------------------------------------------
    # Step 2: Resume Parsing
    # -----------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("STEP 2: Resume Parsing (run_resume_parsing)")
    print("-" * 70)
    resume_output = run_resume_parsing(str(resume_path))
    print(json.dumps(resume_output, indent=2))
    assert resume_output.get("source_type") == "resume", "Step 2 failed: source_type != 'resume'"
    assert len(resume_output.get("skills", [])) > 0, "Step 2 failed: skills list is empty"
    print(f"\n[PASSED] STEP 2 PASSED: Extracted {len(resume_output['skills'])} skills from Resume.")

    # -----------------------------------------------------------------------
    # Step 3: Candidate Profile Save
    # -----------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("STEP 3: Profile Builder (Save Profile pre-filled from Resume)")
    print("-" * 70)
    profile_skills = [
        ProfileSkill(
            skill_name=s["skill_name"],
            category_code=s["category_code"],
            evidence=s.get("evidence", ""),
            confidence=s.get("confidence", 85),
        )
        for s in resume_output["skills"]
    ]

    profile_obj = ProfileModel(
        name="Ananya Rao",
        email="ananya.rao@example.com",
        education="B.Tech in Computer Science, IIT Bombay",
        skills=profile_skills,
        hackathons=["Smart India Hackathon 2024"],
        internships=["Backend Software Engineer Intern"],
        certifications=["AWS Certified Solutions Architect"],
        preferred_roles=["Software Engineer"],
        cv_file="sample_resume.docx",
    )

    save_result = save_profile(profile_obj)
    print(json.dumps(save_result, indent=2))
    assert save_result.get("saved") is True, "Step 3 failed: saved != True"
    saved_profile = save_result["profile"]
    print(f"\n[PASSED] STEP 3 PASSED: Profile saved with profile_id='{save_result['profile_id']}'.")

    # -----------------------------------------------------------------------
    # Step 4: Talent Check
    # -----------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("STEP 4: Talent Check (Company Benchmark 'Google')")
    print("-" * 70)
    talent_check_output = run_talent_check(saved_profile, company="Google")
    print(json.dumps(talent_check_output, indent=2))
    assert "readiness_score" in talent_check_output, "Step 4 failed: readiness_score missing"
    assert "skillset_gap" in talent_check_output, "Step 4 failed: skillset_gap missing"
    print(f"\n[PASSED] STEP 4 PASSED: Talent readiness score = {talent_check_output['readiness_score']}%")

    # -----------------------------------------------------------------------
    # Step 5: Skill Matching
    # -----------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("STEP 5: Skill Matching (Profile vs. Step 1 JD Analytics)")
    print("-" * 70)
    match_output = run_skill_match(saved_profile, jd_output)
    print(json.dumps(match_output, indent=2))
    assert "match_score" in match_output, "Step 5 failed: match_score missing"
    assert "matched_skills" in match_output, "Step 5 failed: matched_skills missing"
    print(f"\n[PASSED] STEP 5 PASSED: Match score = {match_output['match_score']}% ({len(match_output['matched_skills'])} matched, {len(match_output['missing_skills'])} missing)")

    print("\n" + "=" * 70)
    print("ALL 5 INTEGRATION STEPS PASSED SUCCESSFULLY END-TO-END!")
    print("=" * 70)


if __name__ == "__main__":
    main()
