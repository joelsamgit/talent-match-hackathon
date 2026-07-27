"""
models.py — Pydantic data contracts for Skill Matching API.
Shared data contract: Role 5 output model and request models.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CategoryCode(str, Enum):
    DSA   = "DSA"   # Data Structures & Algorithms
    COD   = "COD"   # Coding Proficiency
    OOD   = "OOD"   # Object-Oriented Design & Patterns
    APTI  = "APTI"  # Aptitude, Logic & Problem Solving
    COMM  = "COMM"  # Communication & Collaboration
    AI    = "AI"    # Artificial Intelligence, ML & Data Science
    CLOUD = "CLOUD" # Cloud Platforms & Infrastructure
    SQL   = "SQL"   # Databases & SQL
    SWE   = "SWE"   # Software Engineering Practices
    SYSD  = "SYSD"  # System Design & Architecture
    NETW  = "NETW"  # Computer Networking
    OS    = "OS"    # Operating Systems & Low-level Concepts
    OTHER = "OTHER" # Other real technical / professional skills


class MatchConfidence(str, Enum):
    HIGH   = "high"    # Strong direct match or clear equivalent
    MEDIUM = "medium"  # Partial match or transferable skill
    LOW    = "low"     # Weak match / basic overlap


class ImportanceLevel(str, Enum):
    HIGH   = "high"    # Critical requirement for the role
    MEDIUM = "medium"  # Important secondary skill
    LOW    = "low"     # Nice-to-have skill


# ---------------------------------------------------------------------------
# Output Sub-models
# ---------------------------------------------------------------------------

class MatchedSkill(BaseModel):
    """A skill required by the JD that the candidate possesses."""

    jd_skill_name: str = Field(
        ...,
        description="Name of skill as defined in the Job Description",
        examples=["Data Structures & Algorithms"],
    )
    category_code: str = Field(
        ...,
        description="RADIX category code (e.g. DSA, COD, DB)",
        examples=["DSA"],
    )
    candidate_skill_name: str = Field(
        ...,
        description="Matching skill or experience found in candidate profile",
        examples=["Competitive Programming & Data Structures"],
    )
    match_confidence: MatchConfidence = Field(
        default=MatchConfidence.HIGH,
        description="Confidence level of match: high, medium, or low",
    )
    explanation: str = Field(
        ...,
        description="Reasoning explaining why candidate skill matches the JD requirement",
        examples=["Candidate solved 350+ LeetCode problems in DSA."],
    )


class MissingSkill(BaseModel):
    """A skill required by the JD that the candidate lacks or lacks evidence of."""

    jd_skill_name: str = Field(
        ...,
        description="Name of missing skill from the Job Description",
        examples=["Cloud Infrastructure"],
    )
    category_code: str = Field(
        ...,
        description="RADIX category code",
        examples=["SYSD"],
    )
    importance: ImportanceLevel = Field(
        default=ImportanceLevel.MEDIUM,
        description="Importance level of missing skill: high, medium, or low",
    )
    explanation: str = Field(
        ...,
        description="Explanation of gap and actionable recommendation for candidate",
        examples=["No AWS/Azure experience listed on candidate resume."],
    )


# ---------------------------------------------------------------------------
# Main Data Contract Output Model
# ---------------------------------------------------------------------------

class SkillMatchingOutput(BaseModel):
    """Full structured output for Role 5: Skill Matching."""

    jd_source_file: str = Field(..., description="Filename of source Job Description")
    company: str = Field(..., description="Company name")
    role: str = Field(..., description="Job role title")
    candidate_name: str = Field(..., description="Name of candidate being evaluated")
    match_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Overall match score from 0 to 100",
        examples=[85],
    )
    summary: str = Field(
        ...,
        description="Executive summary of candidate fit for the job role",
    )
    matched_skills: List[MatchedSkill] = Field(
        default_factory=list,
        description="List of skills successfully matched between JD and Candidate",
    )
    missing_skills: List[MissingSkill] = Field(
        default_factory=list,
        description="List of required JD skills missing from Candidate profile",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "jd_source_file": "Google LLC - Software Engineer.pdf",
                "company": "Google LLC",
                "role": "Software Engineer (SWE)",
                "candidate_name": "Ananya Rao",
                "match_score": 85,
                "summary": "Strong candidate for backend/systems software engineering with robust DSA, OS, and System Design background.",
                "matched_skills": [
                    {
                        "jd_skill_name": "Data Structures & Algorithms",
                        "category_code": "DSA",
                        "candidate_skill_name": "Data Structures & Algorithms (350+ competitive programming problems)",
                        "match_confidence": "high",
                        "explanation": "Candidate has extensive competitive programming practice in DSA."
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
        }
    }


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------

class MatchRequest(BaseModel):
    """Request payload for POST /match."""

    jd_analytics: Dict[str, Any] = Field(
        ...,
        description="Full output JSON object from Role 1 (JD Analytics)",
    )
    candidate_profile: Dict[str, Any] = Field(
        ...,
        description="Candidate profile JSON object from Role 2 / Role 3",
    )


class MatchSampleRequest(BaseModel):
    """Request payload for POST /match-sample."""

    jd_filename: str = Field(
        ...,
        description="Filename of sample JD (e.g., 'Google LLC - Software Engineer.pdf')",
        examples=["Google LLC - Software Engineer.pdf"],
    )
    candidate_name: str = Field(
        ...,
        description="Name of sample candidate (e.g., 'Ananya Rao', 'Karthik Subramaniam')",
        examples=["Ananya Rao"],
    )


# ---------------------------------------------------------------------------
# Utility Response Models
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "skill_matching"
    version: str = "1.0.0"


class SamplesResponse(BaseModel):
    sample_jds: List[str]
    sample_candidates: List[str]
