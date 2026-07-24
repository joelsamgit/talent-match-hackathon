"""
scoring.py — Scoring math engine & fallback fuzzy matching logic.

Match Score Formula (0–100):
  Score = (Sum(Matched Skill Weight) / Sum(Total JD Skill Weight)) * 100

  Weighting per matched skill:
    - High confidence match   = 1.0
    - Medium confidence match = 0.6
    - Low confidence match    = 0.3
    - Missing / No match       = 0.0

  Total JD Skill Weight = total count of required skills * 1.0
"""

from __future__ import annotations

from typing import List, Dict, Any, Tuple
from models import MatchConfidence, ImportanceLevel, MatchedSkill, MissingSkill


def calculate_match_score(
    matched_skills: List[Dict[str, Any] | MatchedSkill],
    missing_skills: List[Dict[str, Any] | MissingSkill],
) -> int:
    """
    Calculate normalized 0-100 match score based on weighted skill coverage.

    Args:
        matched_skills: List of matched skill dicts or MatchedSkill instances.
        missing_skills: List of missing skill dicts or MissingSkill instances.

    Returns:
        Integer score between 0 and 100.
    """
    total_skills_count = len(matched_skills) + len(missing_skills)
    if total_skills_count == 0:
        return 0

    achieved_weight = 0.0

    for item in matched_skills:
        if isinstance(item, MatchedSkill):
            conf = item.match_confidence
        else:
            conf_str = item.get("match_confidence", "high").lower()
            try:
                conf = MatchConfidence(conf_str)
            except ValueError:
                conf = MatchConfidence.HIGH

        if conf == MatchConfidence.HIGH:
            achieved_weight += 1.0
        elif conf == MatchConfidence.MEDIUM:
            achieved_weight += 0.6
        elif conf == MatchConfidence.LOW:
            achieved_weight += 0.3
        else:
            achieved_weight += 0.3

    # Assuming maximum possible weight for each JD skill is 1.0
    total_possible_weight = float(total_skills_count)

    score_float = (achieved_weight / total_possible_weight) * 100.0
    score = int(round(score_float))

    # Clamp strictly between 0 and 100
    return max(0, min(100, score))


def fallback_match(jd_analytics: Dict[str, Any], candidate_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fallback deterministic matching when LLM is unavailable.
    Performs string keyword matching between JD required skills and Candidate skills.
    """
    company = jd_analytics.get("company", "Target Company")
    role = jd_analytics.get("role", "Target Role")
    jd_file = jd_analytics.get("source_file", "unknown_jd.pdf")

    candidate_name = candidate_profile.get("candidate_name") or candidate_profile.get("name") or "Candidate"
    candidate_skills = _extract_candidate_skills_list(candidate_profile)

    jd_skills = jd_analytics.get("skills", [])

    matched_skills = []
    missing_skills = []

    for item in jd_skills:
        jd_skill_name = item.get("skill_name", "Skill")
        cat_code = item.get("category_code", "APTI")
        
        # Check fuzzy match against candidate skills
        match_found, match_name, conf = _find_fuzzy_match(jd_skill_name, cat_code, candidate_skills)

        if match_found:
            matched_skills.append({
                "jd_skill_name": jd_skill_name,
                "category_code": cat_code,
                "candidate_skill_name": match_name,
                "match_confidence": conf.value if isinstance(conf, MatchConfidence) else conf,
                "explanation": f"Matched candidate skill '{match_name}' to JD requirement '{jd_skill_name}'.",
            })
        else:
            missing_skills.append({
                "jd_skill_name": jd_skill_name,
                "category_code": cat_code,
                "importance": ImportanceLevel.MEDIUM.value,
                "explanation": f"No direct evidence of '{jd_skill_name}' found in candidate profile.",
            })

    score = calculate_match_score(matched_skills, missing_skills)

    summary = (
        f"{candidate_name} achieved a match score of {score}% for the {role} position at {company}. "
        f"Matched {len(matched_skills)} of {len(jd_skills)} required skills."
    )

    return {
        "jd_source_file": jd_file,
        "company": company,
        "role": role,
        "candidate_name": candidate_name,
        "match_score": score,
        "summary": summary,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
    }


def _extract_candidate_skills_list(candidate_profile: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Extract (skill_name, category_code) tuples from candidate profile dict."""
    result = []
    skills = candidate_profile.get("skills", [])
    
    if isinstance(skills, list):
        for s in skills:
            if isinstance(s, dict):
                name = s.get("skill_name") or s.get("name") or ""
                cat = s.get("category_code") or "APTI"
                if name:
                    result.append((name, cat))
            elif isinstance(s, str):
                result.append((s, "APTI"))
                
    # Also check raw text or summary if available
    raw_text = candidate_profile.get("raw_text", "")
    if raw_text and not result:
        # Fallback split words
        for line in raw_text.splitlines():
            if ":" in line:
                for word in line.split(":", 1)[1].split(","):
                    if word.strip():
                        result.append((word.strip(), "APTI"))

    return result


def _find_fuzzy_match(
    jd_skill: str, cat_code: str, candidate_skills: List[Tuple[str, str]]
) -> Tuple[bool, str, MatchConfidence]:
    """Basic string keyword matching for fallback mode."""
    jd_lower = jd_skill.lower()

    for cand_name, cand_cat in candidate_skills:
        cand_lower = cand_name.lower()

        # Direct category match + partial string overlap
        if cat_code == cand_cat and (jd_lower in cand_lower or cand_lower in jd_lower):
            return True, cand_name, MatchConfidence.HIGH

        # Partial substring match
        if jd_lower in cand_lower or cand_lower in jd_lower:
            return True, cand_name, MatchConfidence.HIGH

        # Word token overlap
        jd_tokens = set(jd_lower.split())
        cand_tokens = set(cand_lower.split())
        overlap = jd_tokens.intersection(cand_tokens) - {"and", "&", "or", "in", "of", "with", "the"}
        
        if len(overlap) >= 1:
            return True, cand_name, MatchConfidence.MEDIUM

    return False, "", MatchConfidence.LOW
