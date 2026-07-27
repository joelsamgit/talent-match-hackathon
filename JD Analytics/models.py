"""
models.py — Pydantic data contracts for JD Analytics API.
Shared data contract: all other roles (Resume Analyzer, Profile Builder, etc.)
must accept this exact shape.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 13 RADIX Skill Categories
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


CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "DSA":   "Data Structures & Algorithms — arrays, trees, graphs, sorting, complexity analysis",
    "COD":   "Coding Proficiency — fluency in specific languages (Python, Java, C++, JS, etc.), code quality",
    "OOD":   "Object-Oriented Design & Patterns — SOLID principles, design patterns, class modeling",
    "APTI":  "Aptitude, Logic & Problem Solving — analytical thinking, quantitative reasoning",
    "COMM":  "Communication & Collaboration — written/verbal communication, teamwork, stakeholder mgmt",
    "AI":    "Artificial Intelligence, ML & Analytics — AI/ML algorithms, data science, statistics, LLMs",
    "CLOUD": "Cloud Platforms & Infrastructure — AWS, Azure, GCP, Docker, Kubernetes, CI/CD deployment",
    "SQL":   "Databases & SQL — relational DB design, SQL queries, NoSQL, data modeling",
    "SWE":   "Software Engineering Practices — Git, testing, Agile, code review",
    "SYSD":  "System Design & Architecture — scalability, distributed systems, microservices, APIs",
    "NETW":  "Computer Networking — TCP/IP, HTTP, DNS, REST, load balancing, security protocols",
    "OS":    "Operating Systems — processes, threads, memory management, Linux/Unix skills",
    "OTHER": "Other Technical/Professional Skills — domain knowledge, tools, legacy systems",
}


# ---------------------------------------------------------------------------
# Skill confidence levels & normalization
# ---------------------------------------------------------------------------

CONFIDENCE_STRING_MAP = {
    "high": 85,
    "medium": 55,
    "low": 25,
}


def normalize_confidence(conf: str | int | None) -> int:
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


class ConfidenceLevel(str, Enum):
    HIGH   = "high"    # Explicitly stated in JD
    MEDIUM = "medium"  # Strongly implied
    LOW    = "low"     # Inferred / background expectation


# ---------------------------------------------------------------------------
# Core models
# ---------------------------------------------------------------------------

class SkillObject(BaseModel):
    """A single skill extracted from a JD or Resume."""

    skill_name: str = Field(
        ...,
        description="Human-readable skill name (e.g. 'Data Structures & Algorithms')",
        examples=["Data Structures & Algorithms", "Python Programming", "System Design"],
    )
    category_code: CategoryCode = Field(
        ...,
        description="One of the 13 RADIX category codes",
    )
    evidence: str = Field(
        ...,
        description="Short verbatim quote or paraphrase from the source document",
        examples=["Strong grasp of data structures and algorithms"],
    )
    confidence: int = Field(
        default=85,
        ge=0,
        le=100,
        description="Confidence score as an integer from 0 to 100",
    )


class JDAnalyticsOutput(BaseModel):
    """Full structured output from the JD Analytics API."""

    source_type: str = Field(default="jd", description="Always 'jd' for this service")
    source_file: str = Field(..., description="Original filename uploaded by the user")
    company: str = Field(..., description="Company name extracted from the JD")
    role: str = Field(..., description="Job role / title extracted from the JD")
    raw_text_length: Optional[int] = Field(
        default=None,
        description="Character count of extracted raw text (useful for debugging)",
    )
    skills: List[SkillObject] = Field(
        ...,
        description="List of skills extracted and categorized from the JD",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "source_type": "jd",
                "source_file": "Google LLC - Software Engineer.pdf",
                "company": "Google LLC",
                "role": "Software Engineer",
                "raw_text_length": 3240,
                "skills": [
                    {
                        "skill_name": "Data Structures & Algorithms",
                        "category_code": "DSA",
                        "evidence": "Strong grasp of data structures and algorithms",
                        "confidence": "high",
                    },
                    {
                        "skill_name": "Python / Java / C++",
                        "category_code": "COD",
                        "evidence": "Experience with Python, Java, or C++",
                        "confidence": "high",
                    },
                ],
            }
        }
    }


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class AnalyzeTextRequest(BaseModel):
    """Body for the POST /analyze-text endpoint."""

    text: str = Field(..., description="Pre-extracted JD text to analyze")
    filename: Optional[str] = Field(
        default="unknown.txt",
        description="Optional filename for display purposes",
    )


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"


class SamplesResponse(BaseModel):
    samples: List[str]
    count: int
