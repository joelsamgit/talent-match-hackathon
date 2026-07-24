"""
RADIX Talent Match — Profile Builder schema & validation.
This is the shared contract everyone else's role reads from.
Keep this file as the single source of truth if you tweak field names with the team.
"""

VALID_CATEGORY_CODES = {
    "DSA", "COD", "OOD", "APTI", "COMM", "AI",
    "CLOUD", "SQL", "SWE", "SYSD", "NETW", "OS", "OTHER"
}

CONFIDENCE_STRING_MAP = {
    "high": 85,
    "medium": 55,
    "low": 25
}


def normalize_confidence(conf):
    """Convert legacy string confidence ('high'/'medium'/'low') or raw values into integer (0-100) or None."""
    if isinstance(conf, str):
        c_lower = conf.strip().lower()
        if c_lower in CONFIDENCE_STRING_MAP:
            return CONFIDENCE_STRING_MAP[c_lower]
        try:
            conf = int(c_lower)
        except ValueError:
            return None
    if isinstance(conf, bool) or not isinstance(conf, int) or not (0 <= conf <= 100):
        return None
    return conf


def empty_profile():
    """Blank profile matching the shared contract shape."""
    return {
        "name": "",
        "email": "",
        "education": "",
        "skills": [],          # list of skill objects, see make_skill()
        "hackathons": [],
        "internships": [],
        "certifications": [],
        "preferred_roles": [],
        "cv_file": ""
    }


def make_skill(skill_name, category_code, evidence="", confidence=None):
    """Build one skill object in the shared skill schema."""
    category_code = category_code.upper()
    if category_code not in VALID_CATEGORY_CODES:
        category_code = "OTHER"
    confidence = normalize_confidence(confidence)
    return {
        "skill_name": skill_name,
        "category_code": category_code,
        "evidence": evidence,
        "confidence": confidence
    }


def validate_profile(profile: dict):
    """
    Returns (is_valid: bool, errors: list[str]).
    Basic validation — required fields, email shape, skills not empty, skill objects well-formed.
    """
    errors = []

    if not profile.get("name", "").strip():
        errors.append("name is required")

    email = profile.get("email", "").strip()
    if not email:
        errors.append("email is required")
    elif "@" not in email or "." not in email.split("@")[-1]:
        errors.append("email looks invalid")

    skills = profile.get("skills", [])
    if not isinstance(skills, list) or len(skills) == 0:
        errors.append("at least one skill is required")
    else:
        for i, s in enumerate(skills):
            if not isinstance(s, dict):
                errors.append(f"skill[{i}] is not an object")
                continue
            if not s.get("skill_name"):
                errors.append(f"skill[{i}] missing skill_name")
            if s.get("category_code") and s.get("category_code") not in VALID_CATEGORY_CODES:
                errors.append(f"skill[{i}] invalid category_code: {s.get('category_code')}")
            conf = s.get("confidence")
            normalized = normalize_confidence(conf)
            s["confidence"] = normalized
            if conf is not None and normalized is None:
                errors.append(f"skill[{i}] invalid confidence: {conf}")

    for list_field in ("hackathons", "internships", "certifications", "preferred_roles"):
        if list_field in profile and not isinstance(profile[list_field], list):
            errors.append(f"{list_field} must be a list")

    return (len(errors) == 0, errors)
