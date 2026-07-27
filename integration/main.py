"""
main.py — Unified FastAPI Backend API for RADIX Talent Match end-to-end flow.

Run:
  uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import os
import shutil
import tempfile
from typing import Any, Dict, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PROFILE_BUILDER_DIR = _REPO_ROOT / "profile_builder" / "backend"

for d in (_REPO_ROOT, _PROFILE_BUILDER_DIR):
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))

from orchestrator import (
    run_jd_analytics,
    run_resume_parsing,
    run_skill_match,
    run_talent_check,
)

# Re-use Profile Builder backend functions & models from real path
from profile_builder.backend.main import (
    Profile as ProfileBuilderModel,
    load_profile as load_profile_builder,
    save_profile as save_profile_builder,
)

app = FastAPI(
    title="RADIX Talent Match — Unified Integration API",
    description="Unified 5-step backend workflow combining JD Analytics, Resume Parsing, Profile Builder, Talent Check, and Skill Matching.",
    version="1.0.0",
)

# Allow React dev server or frontend client
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------

class TalentCheckFlowRequest(BaseModel):
    profile_id: str = Field(..., description="ID of saved profile (e.g. 'arjun_mehta')")
    company: str = Field(..., description="Company name (e.g. 'Google', 'Microsoft')")


class SkillMatchFlowRequest(BaseModel):
    profile_id: str = Field(..., description="ID of saved profile")
    jd_analytics: Dict[str, Any] = Field(..., description="JD Analytics JSON output from Step 1")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "RADIX Talent Match Unified API"}


@app.post("/flow/jd")
async def process_jd(file: UploadFile = File(...)):
    """
    Step 1: Upload Job Description (PDF/DOCX/TXT) -> Extract required skills.
    """
    filename = file.filename or "uploaded_jd.txt"
    suffix = os.path.splitext(filename)[1].lower() or ".txt"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        jd_result = run_jd_analytics(tmp_path)
        jd_result["source_file"] = filename
        return jd_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"JD analysis error: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.post("/flow/resume")
async def process_resume(file: UploadFile = File(...)):
    """
    Step 2: Upload Resume (PDF/DOCX) -> Extract candidate skills & biographical fields.
    """
    filename = file.filename or "uploaded_resume.pdf"
    suffix = os.path.splitext(filename)[1].lower() or ".pdf"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        resume_result = run_resume_parsing(tmp_path)
        resume_result["source_file"] = filename
        return resume_result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Resume parsing error: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.post("/flow/profile")
def save_profile(profile: ProfileBuilderModel):
    """
    Step 3: Save Candidate Profile (reusing Profile Builder backend logic).
    """
    return save_profile_builder(profile)


@app.post("/flow/talent-check")
def execute_talent_check(payload: TalentCheckFlowRequest):
    """
    Step 4: Execute Talent Check comparing saved profile against company benchmarks.
    """
    profile_data = load_profile_builder(payload.profile_id)
    return run_talent_check(profile_data, payload.company)


@app.post("/flow/skill-match")
def execute_skill_match(payload: SkillMatchFlowRequest):
    """
    Step 5: Execute Skill Matching comparing saved profile against JD analytics output.
    """
    profile_data = load_profile_builder(payload.profile_id)
    return run_skill_match(profile_data, payload.jd_analytics)
