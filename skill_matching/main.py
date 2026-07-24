"""
main.py — FastAPI application for Role 5: Skill Matching.

Routes:
  GET  /health            → Liveness check
  GET  /samples           → List available sample JDs and Candidate profiles
  POST /match             → Semantic skill matching between JD Analytics JSON & Candidate Profile JSON
  POST /match-sample      → Test matching between named sample JD & sample Candidate

Run:
  uvicorn main:app --reload --port 8005
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware

# Ensure parent directory is in sys.path so we can import from jd_analytics if available
_THIS_DIR = Path(__file__).parent
_ROOT_DIR = _THIS_DIR.parent
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from models import (
    HealthResponse,
    MatchRequest,
    MatchSampleRequest,
    SamplesResponse,
    SkillMatchingOutput,
)
from matcher import match_skills

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="RADIX Skill Matching API (Role 5)",
    description=(
        "Performs semantic fuzzy skill matching between Job Description analytics "
        "and Candidate profiles using Groq (Llama 3.3 70B). Calculates a weighted 0-100 "
        "Match Score, matched skill evidence, and missing skill gap prioritization."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_JDS_DIR = _ROOT_DIR / "JDs"
_RESUMES_DIR = _ROOT_DIR / "Resumes"


# ---------------------------------------------------------------------------
# Utility & Sample Helper Functions
# ---------------------------------------------------------------------------

def _load_sample_jd_analytics(jd_filename: str) -> Dict[str, Any]:
    """Helper to extract and analyze a sample JD file."""
    pdf_candidates = list(_JDS_DIR.rglob(jd_filename))
    if not pdf_candidates:
        raise HTTPException(
            status_code=404,
            detail=f"Sample JD '{jd_filename}' not found in JDs directory.",
        )
    
    jd_path = pdf_candidates[0]
    
    # Try importing from JD Analytics module
    try:
        try:
            from jd_analytics.extractor import extract_text
            from jd_analytics.analyzer import analyze_jd
        except ImportError:
            import importlib
            extractor = importlib.import_module("JD Analytics.extractor")
            analyzer = importlib.import_module("JD Analytics.analyzer")
            extract_text = extractor.extract_text
            analyze_jd = analyzer.analyze_jd

        file_bytes = jd_path.read_bytes()
        text = extract_text(jd_path.name, file_bytes)
        output = analyze_jd(text, filename=jd_path.name)
        return output.model_dump()
    except Exception as exc:
        # Simple fallback dict if jd_analytics import fails
        return {
            "source_type": "jd",
            "source_file": jd_path.name,
            "company": _infer_company(jd_path.name),
            "role": _infer_role(jd_path.name),
            "skills": [
                {"skill_name": "Data Structures & Algorithms", "category_code": "DSA"},
                {"skill_name": "Operating Systems", "category_code": "OS"},
                {"skill_name": "System Design", "category_code": "SYSD"},
                {"skill_name": "Coding Proficiency", "category_code": "COD"},
            ],
        }


def _load_sample_candidate_profile(candidate_name: str) -> Dict[str, Any]:
    """Helper to extract text or build candidate profile from sample Resumes."""
    # Find matching candidate resume PDF/DOCX
    matching_files = [
        f for f in _RESUMES_DIR.rglob("*.*")
        if candidate_name.lower() in f.name.lower()
    ]
    
    raw_text = ""
    resume_file = f"{candidate_name}.pdf"

    if matching_files:
        resume_path = matching_files[0]
        resume_file = resume_path.name
        try:
            try:
                from jd_analytics.extractor import extract_text
            except ImportError:
                import importlib
                extractor = importlib.import_module("JD Analytics.extractor")
                extract_text = extractor.extract_text

            raw_text = extract_text(resume_path.name, resume_path.read_bytes())
        except Exception:
            raw_text = f"Resume content for {candidate_name}"

    # Build representative skills based on sample candidate name
    skills = _get_mock_candidate_skills(candidate_name)

    return {
        "candidate_name": candidate_name,
        "resume_file": resume_file,
        "raw_text": raw_text,
        "skills": skills,
    }


def _get_mock_candidate_skills(candidate_name: str) -> list[dict[str, str]]:
    name_lower = candidate_name.lower()
    
    if "ananya" in name_lower:
        # Ananya Rao — Systems / SWE candidate
        return [
            {"skill_name": "Data Structures & Algorithms (350+ LeetCode problems)", "category_code": "DSA"},
            {"skill_name": "C++ & Python Programming", "category_code": "COD"},
            {"skill_name": "Object-Oriented Design & Design Patterns", "category_code": "OOD"},
            {"skill_name": "System Design & Distributed Cache", "category_code": "SYSD"},
            {"skill_name": "Operating Systems & Linux Multithreading", "category_code": "OS"},
            {"skill_name": "Networking (TCP/IP, HTTP REST APIs)", "category_code": "NETW"},
            {"skill_name": "Git, CI/CD, Unit Testing", "category_code": "SWE"},
            {"skill_name": "Technical Writing & Presentation", "category_code": "COMM"},
        ]
    elif "karthik" in name_lower:
        # Karthik Subramaniam — Data Analyst candidate
        return [
            {"skill_name": "SQL & Relational Database Querying", "category_code": "DB"},
            {"skill_name": "Power BI & Tableau Dashboarding", "category_code": "DATA"},
            {"skill_name": "Data Analysis & Statistics", "category_code": "DATA"},
            {"skill_name": "Excel & Business Intelligence", "category_code": "DATA"},
            {"skill_name": "Python Data Manipulation (pandas, numpy)", "category_code": "COD"},
            {"skill_name": "Quantitative Aptitude & Problem Solving", "category_code": "APTI"},
            {"skill_name": "Stakeholder Communication", "category_code": "COMM"},
        ]
    elif "priya" in name_lower:
        # Priya Menon — Application Support candidate
        return [
            {"skill_name": "SQL Querying & Database Maintenance", "category_code": "DB"},
            {"skill_name": "Linux/Unix Shell Scripting & OS Administration", "category_code": "OS"},
            {"skill_name": "Networking Protocols (TCP/IP, DNS, Firewalls)", "category_code": "NETW"},
            {"skill_name": "Incident Management & Ticketing (Jira, ServiceNow)", "category_code": "SWE"},
            {"skill_name": "Client Technical Support & Shift Work", "category_code": "MGMT"},
            {"skill_name": "Logical Troubleshooting & Problem Solving", "category_code": "APTI"},
            {"skill_name": "Verbal & Written Communication", "category_code": "COMM"},
        ]
    else:
        # Rohan Verma or General candidate
        return [
            {"skill_name": "Python & Java Programming", "category_code": "COD"},
            {"skill_name": "SQL & Relational Databases", "category_code": "DB"},
            {"skill_name": "Data Structures Basics", "category_code": "DSA"},
            {"skill_name": "Agile Software Development", "category_code": "SWE"},
            {"skill_name": "Teamwork & Communication", "category_code": "COMM"},
        ]


def _infer_company(filename: str) -> str:
    stem = Path(filename).stem
    return stem.split(" - ")[0].strip() if " - " in stem else "Target Company"


def _infer_role(filename: str) -> str:
    stem = Path(filename).stem
    return stem.split(" - ", 1)[1].strip() if " - " in stem else "Target Role"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["Utility"])
async def health():
    """Liveness check — returns OK if the service is operational."""
    return HealthResponse(status="ok", service="skill_matching", version="1.0.0")


@app.get("/samples", response_model=SamplesResponse, tags=["Utility"])
async def list_samples():
    """List all available sample JDs and sample candidates for testing."""
    jd_files = []
    if _JDS_DIR.exists():
        jd_files = sorted(f.name for f in _JDS_DIR.rglob("*.pdf"))

    candidates = ["Ananya Rao", "Karthik Subramaniam", "Priya Menon", "Rohan Verma"]
    return SamplesResponse(sample_jds=jd_files, sample_candidates=candidates)


@app.post("/match", response_model=SkillMatchingOutput, tags=["Matching"])
async def match_endpoint(body: MatchRequest = Body(...)):
    """
    Perform semantic skill matching between JD Analytics output and Candidate Profile.

    - **jd_analytics**: Output JSON from Role 1 (JD Analytics)
    - **candidate_profile**: Output JSON from Role 2 / Role 3 (Resume Analyzer / Profile Builder)

    Returns 0-100 Match Score, matched skills with evidence, and missing skill gaps.
    """
    if not body.jd_analytics:
        raise HTTPException(status_code=400, detail="'jd_analytics' field cannot be empty.")
    if not body.candidate_profile:
        raise HTTPException(status_code=400, detail="'candidate_profile' field cannot be empty.")

    try:
        output = match_skills(body.jd_analytics, body.candidate_profile)
        return output
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Skill matching failed: {exc}")


@app.post("/match-sample", response_model=SkillMatchingOutput, tags=["Matching"])
async def match_sample_endpoint(body: MatchSampleRequest):
    """
    Perform skill matching against any combination of sample JDs and sample Candidates.

    Example payload:
    ```json
    {
      "jd_filename": "Google LLC - Software Engineer.pdf",
      "candidate_name": "Ananya Rao"
    }
    ```
    """
    try:
        jd_analytics = _load_sample_jd_analytics(body.jd_filename)
        candidate_profile = _load_sample_candidate_profile(body.candidate_name)
        output = match_skills(jd_analytics, candidate_profile)
        return output
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Sample matching failed: {exc}")


# ---------------------------------------------------------------------------
# Dev Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8005"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
