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
    confidence: CONFIDENCE_LEVELS


class ExtractedSkillList(BaseModel):
    """Container for the full list of skills extracted from one resume."""
    schema_version: str = Field(default="1.0")
    source_type: Literal["resume"] = "resume"
    source_file: str
    skills: list[Skill] = Field(default_factory=list)
    extracted_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ---------------------------------------------------------------------------
# Structured biographical fields
# ---------------------------------------------------------------------------
class ProjectEntry(BaseModel):
    """A project listed on the resume."""
    title: str
    description: str


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
