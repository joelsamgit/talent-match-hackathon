"""
routers/resume_parsing.py — FastAPI endpoint orchestrating the full resume-parsing pipeline.

POST /parse-resume accepts a file upload (PDF or DOCX) and returns a ParseResult
containing extracted skills, structured biographical fields, extraction method,
and any warnings generated along the way.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, File, HTTPException, UploadFile

from extraction import extract_text
from llm_client import extract_skills, extract_structured_fields, verify_skill_coverage
from schema import ExtractedSkillList, ParseResult, StructuredFields
from section_mapper import map_sections

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Resume Parsing"])

# Maximum upload size: 20 MB (generous for resumes)
_MAX_FILE_SIZE = 20 * 1024 * 1024

_ALLOWED_EXTENSIONS = {".pdf", ".docx"}


def _validate_extension(filename: str) -> str | None:
    """Return the lowered extension if allowed, or None."""
    lower = filename.lower()
    for ext in _ALLOWED_EXTENSIONS:
        if lower.endswith(ext):
            return ext
    return None


@router.post("/parse-resume", response_model=ParseResult)
async def parse_resume(file: UploadFile = File(...)):
    """
    Parse a resume file and return structured skills + biographical fields.

    Accepts PDF or DOCX uploads. Runs the full 7-stage pipeline:
    text extraction → section mapping → skill extraction → field extraction
    → validation → merge.
    """
    filename = file.filename or "unknown"
    warnings: list[str] = []

    # -----------------------------------------------------------------------
    # Pre-checks
    # -----------------------------------------------------------------------
    ext = _validate_extension(filename)
    if ext is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: '{filename}'. Only .pdf and .docx are accepted.",
        )

    # Read file bytes
    try:
        file_bytes = await file.read()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read uploaded file: {exc}")

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")

    if len(file_bytes) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(file_bytes)} bytes). Maximum is {_MAX_FILE_SIZE} bytes.",
        )

    t0 = time.time()

    # -----------------------------------------------------------------------
    # Stage 1 — Text extraction
    # -----------------------------------------------------------------------
    extraction = extract_text(file_bytes, filename)
    warnings.extend(extraction.warnings)

    if not extraction.full_text.strip():
        # Return empty-but-valid result instead of crashing
        warnings.append("Resume text is empty after extraction. Returning empty result.")
        return ParseResult(
            skills=ExtractedSkillList(source_file=filename, skills=[]),
            fields=StructuredFields(),
            extraction_method=extraction.extraction_method,
            warnings=warnings,
        )

    logger.info(
        "Extraction done: %d lines, %d chars, method=%s",
        len(extraction.lines),
        len(extraction.full_text),
        extraction.extraction_method,
    )

    # -----------------------------------------------------------------------
    # Stage 2 — Heuristic section mapping
    # -----------------------------------------------------------------------
    sections = map_sections(extraction.lines)
    logger.info("Section mapping: %d sections detected", len(sections))

    # -----------------------------------------------------------------------
    # Stage 3 — Skill extraction (LLM)
    # -----------------------------------------------------------------------
    is_ocr = extraction.extraction_method in ("ocr", "mixed")
    skills, skill_warnings = extract_skills(
        full_text=extraction.full_text,
        sections=sections,
        is_ocr=is_ocr,
    )
    warnings.extend(skill_warnings)

    # -----------------------------------------------------------------------
    # Stage 4 — Structured field extraction (LLM)
    # -----------------------------------------------------------------------
    fields, field_warnings = extract_structured_fields(extraction.full_text)
    warnings.extend(field_warnings)

    # -----------------------------------------------------------------------
    # Stage 7 — Validation & Merge
    # -----------------------------------------------------------------------
    coverage_warnings = verify_skill_coverage(sections, skills)
    warnings.extend(coverage_warnings)
    
    elapsed = time.time() - t0
    logger.info("Pipeline complete in %.2fs: %d skills extracted", elapsed, len(skills))

    return ParseResult(
        skills=ExtractedSkillList(
            source_file=filename,
            skills=skills,
            extracted_at=datetime.now(timezone.utc).isoformat(),
        ),
        fields=fields if fields else StructuredFields(),
        extraction_method=extraction.extraction_method,
        warnings=warnings,
    )
