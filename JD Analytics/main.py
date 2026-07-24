"""
main.py — FastAPI application for JD Analytics.

Routes:
  GET  /health                      → liveness check
  GET  /samples                     → list available sample JDs
  POST /analyze                     → upload PDF/DOCX → structured skills JSON
  POST /analyze-text                → send raw text → structured skills JSON
  POST /analyze-sample/{filename}   → analyze a named sample JD (no upload needed)

Run:
  uvicorn main:app --reload --port 8001
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from analyzer import analyze_jd
from extractor import extract_text
from models import (
    AnalyzeTextRequest,
    HealthResponse,
    JDAnalyticsOutput,
    SamplesResponse,
)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="RADIX JD Analytics API",
    description=(
        "Extracts and categorizes skills from Job Description files (PDF/DOCX) "
        "using Groq (Llama 3.3 70B). Maps skills to the 12 RADIX categories."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow any frontend (React/Next.js dev server, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Locate the JDs sample directory relative to this file
_THIS_DIR = Path(__file__).parent
_SAMPLES_DIR = _THIS_DIR.parent / "JDs"

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}
MAX_FILE_SIZE_MB = 10


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["Utility"])
async def health():
    """Liveness check — returns OK if the server is running."""
    return HealthResponse(status="ok", version="1.0.0")


@app.get("/samples", response_model=SamplesResponse, tags=["Utility"])
async def list_samples():
    """
    List all available sample JD files that can be tested via
    POST /analyze-sample/{filename}.
    """
    if not _SAMPLES_DIR.exists():
        return SamplesResponse(samples=[], count=0)

    files = []
    for ext in ALLOWED_EXTENSIONS:
        files.extend(_SAMPLES_DIR.rglob(f"*{ext}"))

    names = sorted(f.name for f in files)
    return SamplesResponse(samples=names, count=len(names))


@app.post("/analyze", response_model=JDAnalyticsOutput, tags=["Analysis"])
async def analyze_file(file: UploadFile = File(...)):
    """
    Upload a PDF or DOCX job description file.
    Returns structured skill extraction mapped to the 12 RADIX categories.
    """
    # Validate extension
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Please upload a .pdf or .docx file.",
        )

    # Read file bytes
    file_bytes = await file.read()

    # Validate file size
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f} MB). Maximum allowed: {MAX_FILE_SIZE_MB} MB.",
        )

    # Extract text
    try:
        text = extract_text(file.filename, file_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # Analyze with Groq
    try:
        result = analyze_jd(text=text, filename=file.filename)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return result


@app.post("/analyze-text", response_model=JDAnalyticsOutput, tags=["Analysis"])
async def analyze_text_endpoint(body: AnalyzeTextRequest):
    """
    Send pre-extracted JD text for analysis.
    Useful for Role 3 (Profile Builder) to pass text without re-uploading a file.
    """
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="'text' field cannot be empty.")

    try:
        result = analyze_jd(text=body.text, filename=body.filename or "unknown.txt")
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return result


@app.post(
    "/analyze-sample/{filename:path}",
    response_model=JDAnalyticsOutput,
    tags=["Analysis"],
)
async def analyze_sample(filename: str):
    """
    Analyze one of the bundled sample JDs by filename (no upload required).
    Use GET /samples to see what's available.

    Example: POST /analyze-sample/Google LLC - Software Engineer.pdf
    """
    # Search for the file in the samples directory
    candidates = list(_SAMPLES_DIR.rglob(filename))
    if not candidates:
        raise HTTPException(
            status_code=404,
            detail=f"Sample file '{filename}' not found. Use GET /samples to list available files.",
        )

    sample_path = candidates[0]
    file_bytes = sample_path.read_bytes()

    try:
        text = extract_text(sample_path.name, file_bytes)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    try:
        result = analyze_jd(text=text, filename=sample_path.name)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return result


# ---------------------------------------------------------------------------
# Dev entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8001"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
