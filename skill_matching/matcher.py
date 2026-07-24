"""
matcher.py — Groq (Llama 3.3 70B) powered semantic skill matching engine.

Flow:
  1. Parse JD analytics & candidate profile inputs.
  2. Build system + user prompt for Groq with 12 RADIX categories context.
  3. Execute LLM call with response_format={"type": "json_object"}.
  4. Parse LLM JSON output, normalize category codes & match confidence levels.
  5. Compute mathematical Match Score (0-100) using scoring.py.
  6. Return validated SkillMatchingOutput instance.
"""

from __future__ import annotations

import json
import os
from typing import Dict, Any

from groq import Groq
from dotenv import load_dotenv

from models import (
    CategoryCode,
    MatchConfidence,
    ImportanceLevel,
    MatchedSkill,
    MissingSkill,
    SkillMatchingOutput,
)
from scoring import calculate_match_score, fallback_match

load_dotenv()

# ---------------------------------------------------------------------------
# Groq client (lazily initialized)
# ---------------------------------------------------------------------------

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. "
                "Create a .env file with GROQ_API_KEY=your_key_here. "
                "Get a free key at https://console.groq.com"
            )
        _client = Groq(api_key=api_key)
    return _client


MODEL = "llama-3.3-70b-versatile"

# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an expert technical talent recruiter and skills matching specialist.

Your task is to evaluate a candidate's background against a Job Description (JD) and perform a deep semantic skill match across the 12 RADIX skill categories:
- DSA: Data Structures & Algorithms
- COD: Coding Proficiency
- OOD: Object-Oriented Design & Patterns
- SYSD: System Design & Architecture
- OS: Operating Systems & Low-level Concepts
- NETW: Computer Networking
- DB: Databases & SQL
- SWE: Software Engineering Practices
- DATA: Data Science, ML & Analytics
- APTI: Aptitude, Logic & Problem Solving
- COMM: Communication & Collaboration
- MGMT: Project & Product Management

## Rules for Semantic Matching:
1. Account for phrasing variations, synonyms, and domain-equivalent experience:
   - "PostgreSQL" or "MySQL" matches "SQL Querying / Databases" (DB)
   - "scikit-learn", "PyTorch", or "TensorFlow" matches "Machine Learning Fundamentals" (DATA)
   - "Built distributed cache in C++" matches "Operating Systems / System Design" (OS / SYSD)
   - "Competitive programming (300+ solved)" matches "Data Structures & Algorithms" (DSA)
2. Every skill required in the JD MUST be classified into either:
   - "matched_skills": The candidate possesses this skill or strong equivalent.
   - "missing_skills": The candidate lacks this skill or has insufficient evidence.
3. For each matched skill:
   - "match_confidence": "high" (direct experience), "medium" (equivalent / partial experience), or "low" (basic familiarity).
   - "explanation": Concise evidence-based justification referencing candidate profile.
4. For each missing skill:
   - "importance": "high" (critical core skill), "medium" (important skill), or "low" (nice-to-have).
   - "explanation": Actionable description of the gap and what the candidate needs to build.
5. Provide a 2-3 sentence executive "summary" evaluating overall candidate fit.
6. Return ONLY valid JSON format — no markdown, no prose wrapper.

## Strict JSON Output Schema:
{
  "summary": "<executive summary of candidate fit>",
  "matched_skills": [
    {
      "jd_skill_name": "<skill name from JD>",
      "category_code": "<one of the 12 RADIX codes>",
      "candidate_skill_name": "<matching skill/experience from candidate profile>",
      "match_confidence": "<high|medium|low>",
      "explanation": "<why it matches>"
    }
  ],
  "missing_skills": [
    {
      "jd_skill_name": "<missing skill name from JD>",
      "category_code": "<one of the 12 RADIX codes>",
      "importance": "<high|medium|low>",
      "explanation": "<description of gap & actionable advice>"
    }
  ]
}
"""


def _build_user_prompt(jd_analytics: Dict[str, Any], candidate_profile: Dict[str, Any]) -> str:
    company = jd_analytics.get("company", "Target Company")
    role = jd_analytics.get("role", "Target Role")
    jd_skills = jd_analytics.get("skills", [])

    candidate_name = (
        candidate_profile.get("candidate_name")
        or candidate_profile.get("name")
        or "Candidate"
    )

    return f"""Perform semantic skill matching between the Job Description and Candidate Profile.

--- JOB DESCRIPTION ---
Company: {company}
Role: {role}
Required Skills: {json.dumps(jd_skills, indent=2)}

--- CANDIDATE PROFILE ---
Candidate Name: {candidate_name}
Candidate Profile Details: {json.dumps(candidate_profile, indent=2)}

Return ONLY the JSON object described in system instructions.
"""


# ---------------------------------------------------------------------------
# Core Match Function
# ---------------------------------------------------------------------------

def match_skills(
    jd_analytics: Dict[str, Any],
    candidate_profile: Dict[str, Any],
) -> SkillMatchingOutput:
    """
    Perform semantic skill matching between JD analytics and Candidate profile.

    Args:
        jd_analytics: Dict from Role 1 output
        candidate_profile: Dict from Role 2 or Role 3 output

    Returns:
        Validated SkillMatchingOutput object.
    """
    try:
        client = _get_client()
    except RuntimeError:
        # Fallback if GROQ_API_KEY is not set
        res_dict = fallback_match(jd_analytics, candidate_profile)
        return SkillMatchingOutput(**res_dict)

    user_prompt = _build_user_prompt(jd_analytics, candidate_profile)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=4096,
        )
        raw_json = response.choices[0].message.content
        data = json.loads(raw_json)
    except Exception:
        # Fallback to rule-based matcher if API fails
        res_dict = fallback_match(jd_analytics, candidate_profile)
        return SkillMatchingOutput(**res_dict)

    # Process and validate matched skills
    matched_skills: list[MatchedSkill] = []
    valid_codes = {c.value for c in CategoryCode}

    for item in data.get("matched_skills", []):
        cat_code = str(item.get("category_code", "APTI")).upper()
        if cat_code not in valid_codes:
            cat_code = "APTI"

        conf_str = str(item.get("match_confidence", "high")).lower()
        try:
            confidence = MatchConfidence(conf_str)
        except ValueError:
            confidence = MatchConfidence.HIGH

        matched_skills.append(
            MatchedSkill(
                jd_skill_name=item.get("jd_skill_name", "Skill"),
                category_code=cat_code,
                candidate_skill_name=item.get("candidate_skill_name", "Candidate Skill"),
                match_confidence=confidence,
                explanation=item.get("explanation", "Matched skill based on profile evidence."),
            )
        )

    # Process and validate missing skills
    missing_skills: list[MissingSkill] = []
    for item in data.get("missing_skills", []):
        cat_code = str(item.get("category_code", "APTI")).upper()
        if cat_code not in valid_codes:
            cat_code = "APTI"

        imp_str = str(item.get("importance", "medium")).lower()
        try:
            importance = ImportanceLevel(imp_str)
        except ValueError:
            importance = ImportanceLevel.MEDIUM

        missing_skills.append(
            MissingSkill(
                jd_skill_name=item.get("jd_skill_name", "Skill"),
                category_code=cat_code,
                importance=importance,
                explanation=item.get("explanation", "Skill gap identified."),
            )
        )

    # Compute normalized Match Score using mathematical formula
    score = calculate_match_score(matched_skills, missing_skills)

    # Construct final metadata
    company = jd_analytics.get("company") or "Target Company"
    role = jd_analytics.get("role") or "Target Role"
    jd_file = jd_analytics.get("source_file") or "unknown_jd.pdf"
    candidate_name = (
        candidate_profile.get("candidate_name")
        or candidate_profile.get("name")
        or "Candidate"
    )

    summary = data.get("summary") or (
        f"{candidate_name} achieved a match score of {score}% for {role} at {company}."
    )

    return SkillMatchingOutput(
        jd_source_file=jd_file,
        company=company,
        role=role,
        candidate_name=candidate_name,
        match_score=score,
        summary=summary,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
    )
