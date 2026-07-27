"""
schema.py — Pydantic v2 data contract for the RADIX Talent Match Resume Parsing module.

These models define the exact output shape consumed by the downstream Profile Builder module.
All fields, defaults, and constraints match the agreed-upon data contract.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Category codes accepted by the pipeline
# ---------------------------------------------------------------------------
CATEGORY_CODES = Literal[
    "DSA", "COD", "OOD", "APTI", "COMM",
    "AI", "CLOUD", "SQL", "SWE", "SYSD",
    "NETW", "OS", "OTHER",
]

CONFIDENCE_STRING_MAP = {
    "high": 85,
    "medium": 55,
    "low": 25,
}


def normalize_confidence(conf: str | int | float | None) -> int:
    """Convert string confidence ('high'/'medium'/'low') or raw values to int 0-100 (default 85)."""
    if isinstance(conf, str):
        c_lower = conf.strip().lower()
        if c_lower in CONFIDENCE_STRING_MAP:
            return CONFIDENCE_STRING_MAP[c_lower]
        try:
            val = int(c_lower)
            return max(0, min(100, val))
        except ValueError:
            return 85
    if isinstance(conf, (int, float)) and not isinstance(conf, bool):
        return max(0, min(100, int(conf)))
    return 85


CONFIDENCE_LEVELS = Literal["high", "medium", "low"]
EXTRACTION_METHOD = Literal["text", "ocr", "mixed"]


# ---------------------------------------------------------------------------
# Skill-level models
# ---------------------------------------------------------------------------
class Skill(BaseModel):
    """A single extracted skill with evidence and confidence."""
    skill_name: str
    category_code: CATEGORY_CODES
    evidence: str
    confidence: int = Field(default=85, ge=0, le=100)


class ExtractedSkillList(BaseModel):
    """Container for the full list of skills extracted from one resume."""
    schema_version: str = Field(default="1.0")
    source_type: Literal["resume"] = "resume"
    source_file: str
    company: str = Field(default="Candidate Resume")
    role: str = Field(default="Applicant")
    skills: list[Skill] = Field(default_factory=list)
    extracted_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ---------------------------------------------------------------------------
# Structured biographical fields
# ---------------------------------------------------------------------------
class ProjectEntry(BaseModel):
    """A project listed on the resume."""
    title: Optional[str] = ""
    description: Optional[str] = ""


class StructuredFields(BaseModel):
    """Biographical / educational fields pulled from the resume."""
    name: Optional[str] = None
    email: Optional[str] = None
    education: Optional[str] = None
    experience_years_estimate: Optional[float] = None
    projects: list[ProjectEntry] = Field(default_factory=list)
    internships: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Top-level parse result — the contract handed to Profile Builder
# ---------------------------------------------------------------------------
class ParseResult(BaseModel):
    """Full output of the resume-parsing pipeline for one file."""
    skills: ExtractedSkillList
    fields: StructuredFields
    extraction_method: EXTRACTION_METHOD
    warnings: list[str] = Field(default_factory=list)

    def to_contract_dict(self) -> dict:
        """Export output matching shared JD Analytics / Resume Parsing output contract."""
        skills_data = []
        for s in self.skills.skills:
            conf_val = s.confidence if isinstance(s.confidence, int) else normalize_confidence(s.confidence)
            skills_data.append({
                "skill_name": s.skill_name,
                "category_code": s.category_code,
                "evidence": s.evidence,
                "confidence": conf_val,
            })
        return {
            "source_type": "resume",
            "source_file": self.skills.source_file,
            "company": self.skills.company,
            "role": self.skills.role,
            "skills": skills_data,
            "fields": {
                "name": self.fields.name or "",
                "email": self.fields.email or "",
                "education": self.fields.education or "",
                "experience_years_estimate": self.fields.experience_years_estimate,
                "projects": [p.model_dump() for p in self.fields.projects],
                "internships": self.fields.internships,
                "certifications": self.fields.certifications,
            },
        }

