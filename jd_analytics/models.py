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
# 12 RADIX Skill Categories
# ---------------------------------------------------------------------------

class CategoryCode(str, Enum):
    DSA   = "DSA"   # Data Structures & Algorithms
    COD   = "COD"   # Coding Proficiency (language fluency, clean code)
    OOD   = "OOD"   # Object-Oriented Design & Patterns
    SYSD  = "SYSD"  # System Design & Architecture
    OS    = "OS"    # Operating Systems & Low-level Concepts
    NETW  = "NETW"  # Computer Networking
    DB    = "DB"    # Databases & SQL
    SWE   = "SWE"   # Software Engineering Practices (CI/CD, testing, version control)
    DATA  = "DATA"  # Data Science, ML & Analytics
    APTI  = "APTI"  # Aptitude, Logic & Problem Solving
    COMM  = "COMM"  # Communication & Collaboration
    MGMT  = "MGMT"  # Project & Product Management


CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "DSA":  "Data Structures & Algorithms — arrays, trees, graphs, sorting, complexity analysis",
    "COD":  "Coding Proficiency — fluency in specific languages (Python, Java, C++, JS, etc.), code quality",
    "OOD":  "Object-Oriented Design & Patterns — SOLID principles, design patterns, class modeling",
    "SYSD": "System Design & Architecture — scalability, distributed systems, microservices, APIs",
    "OS":   "Operating Systems — processes, threads, memory management, Linux/Unix skills",
    "NETW": "Computer Networking — TCP/IP, HTTP, DNS, REST, load balancing, security protocols",
    "DB":   "Databases & SQL — relational DB design, SQL queries, NoSQL, data modeling",
    "SWE":  "Software Engineering Practices — Git, CI/CD, testing, Agile, code review",
    "DATA": "Data Science, ML & Analytics — statistics, ML algorithms, data pipelines, BI tools",
    "APTI": "Aptitude, Logic & Problem Solving — analytical thinking, quantitative reasoning",
    "COMM": "Communication & Collaboration — written/verbal communication, teamwork, stakeholder mgmt",
    "MGMT": "Project & Product Management — planning, prioritization, delivery, leadership",
}


# ---------------------------------------------------------------------------
# Skill confidence levels
# ---------------------------------------------------------------------------

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
        description="One of the 12 RADIX category codes",
    )
    evidence: str = Field(
        ...,
        description="Short verbatim quote or paraphrase from the source document",
        examples=["Strong grasp of data structures and algorithms"],
    )
    confidence: ConfidenceLevel = Field(
        default=ConfidenceLevel.HIGH,
        description="How confident the model is that this skill is required",
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
