"""
main.py — Application entrypoint for the RADIX Talent Match Resume Parsing service.

Mounts the resume-parsing router and provides a health-check endpoint.
Run with: uvicorn main:app --reload
"""

from fastapi import FastAPI

from routers.resume_parsing import router as resume_router

app = FastAPI(
    title="RADIX Talent Match — Resume Parser",
    description="Extracts structured skills and biographical fields from PDF/DOCX resumes.",
    version="0.1.0",
)

app.include_router(resume_router)


@app.get("/health")
async def health_check():
    """Simple liveness probe."""
    return {"status": "ok"}
