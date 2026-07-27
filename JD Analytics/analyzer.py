"""
analyzer.py — Groq (Llama 3.3 70B) powered JD skill extraction.

Flow:
  1. Build system + user prompt with few-shot examples
  2. Call Groq with response_format={"type": "json_object"}
  3. Parse + validate via Pydantic → JDAnalyticsOutput

Environment:
  GROQ_API_KEY  — set in .env file
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from groq import Groq
from dotenv import load_dotenv

from models import (
    CategoryCode,
    CATEGORY_DESCRIPTIONS,
    ConfidenceLevel,
    JDAnalyticsOutput,
    SkillObject,
    normalize_confidence,
)

load_dotenv()

# ---------------------------------------------------------------------------
# Groq client (lazily initialised so import doesn't fail without a key)
# ---------------------------------------------------------------------------

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. "
                "Create a .env file with GROQ_API_KEY=your_key_here. "
                "Get a free key at https://console.groq.com"
            )
        _client = Groq(api_key=api_key)
    return _client


MODEL = "llama-3.1-8b-instant"

# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

_CATEGORY_LIST = "\n".join(
    f'  - "{code}": {desc}'
    for code, desc in CATEGORY_DESCRIPTIONS.items()
)

SYSTEM_PROMPT = f"""You are an expert technical recruiter and skills analyst.

Your task is to analyze a Job Description (JD) and extract all the skills, competencies,
and requirements mentioned — then map each one to exactly one of the 13 RADIX skill categories.

## The 13 RADIX Categories (use ONLY these codes):
{_CATEGORY_LIST}

## Rules:
1. Extract every distinct skill, tool, or competency mentioned in the JD.
2. Map each to exactly ONE category code from the list above.
3. Provide a short verbatim quote (≤ 30 words) from the JD as "evidence".
4. Set "confidence" to an integer from 0-100 (85 for high/explicit, 55 for medium/implied, 25 for low/inferred).
5. Focus especially on "Key Responsibilities", "Requirements", and "What We're Looking For" sections.
6. Extract the company name and job role from the JD text.
7. Return ONLY valid JSON — no markdown, no prose, no code fences.

## Output format (strict JSON):
{{
  "company": "<company name>",
  "role": "<job title>",
  "skills": [
    {{
      "skill_name": "<human readable skill name>",
      "category_code": "<one of the 13 codes>",
      "evidence": "<short verbatim quote from JD>",
      "confidence": <integer 0-100>
    }}
  ]
}}
"""


# ---------------------------------------------------------------------------
# Core analysis function
# ---------------------------------------------------------------------------

def analyze_jd(text: str, filename: str = "unknown.txt") -> JDAnalyticsOutput:
    """
    Analyze pre-extracted JD text using Groq (Llama 3.3 70B).

    Args:
        text: Raw character text of the job description
        filename: Optional filename used for metadata inference

    Returns:
        Structured JDAnalyticsOutput object
    """
    if not text.strip():
        return JDAnalyticsOutput(
            source_type="jd",
            source_file=filename,
            company=_infer_company(filename),
            role=_infer_role(filename),
            raw_text_length=0,
            skills=[],
        )

    client = _get_client()

    # Truncate if extremely long (Groq free tier: 6k tokens/min)
    # ~4 chars per token → 12,000 chars ≈ 3,000 tokens (leaves room for response)
    max_chars = 12_000
    if len(text) > max_chars:
        text = text[:max_chars] + "\n[...text truncated for token limit...]"

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Document Filename: {filename}\n\nJob Description Text:\n{text}",
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.1,   # Low temp → consistent, structured output
            max_tokens=4096,
        )
    except Exception as exc:
        raise RuntimeError(f"Groq API call failed: {exc}") from exc

    raw_content = response.choices[0].message.content

    # Parse JSON
    try:
        data = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Groq returned invalid JSON: {exc}\nRaw response: {raw_content[:500]}"
        ) from exc

    # Validate and coerce skills
    skills: list[SkillObject] = []
    valid_codes = {c.value for c in CategoryCode}

    for item in data.get("skills", []):
        code = item.get("category_code", "").upper()
        # Map legacy DB/DATA/MGMT codes if hallucinated
        code_map = {"DB": "SQL", "DATA": "AI", "MGMT": "OTHER"}
        code = code_map.get(code, code)
        # Gracefully handle any hallucinated codes
        if code not in valid_codes:
            code = _fuzzy_match_code(code, valid_codes)

        confidence_val = normalize_confidence(item.get("confidence", 85))

        skills.append(
            SkillObject(
                skill_name=item.get("skill_name", "Unknown Skill"),
                category_code=CategoryCode(code),
                evidence=item.get("evidence", ""),
                confidence=confidence_val,
            )
        )

    return JDAnalyticsOutput(
        source_type="jd",
        source_file=filename,
        company=data.get("company") or _infer_company(filename),
        role=data.get("role") or _infer_role(filename),
        raw_text_length=len(text),
        skills=skills,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fuzzy_match_code(code: str, valid_codes: set[str]) -> str:
    """Best-effort fuzzy match for hallucinated category codes."""
    # Direct prefix match
    for valid in valid_codes:
        if valid.startswith(code[:3]):
            return valid
    # Fallback to APTI (general)
    return "APTI"


def _infer_company(filename: str) -> str:
    """Try to extract company from filename like 'Google LLC - Software Engineer.pdf'."""
    stem = Path(filename).stem
    if " - " in stem:
        return stem.split(" - ")[0].strip()
    return "Unknown Company"


def _infer_role(filename: str) -> str:
    """Try to extract role from filename like 'Google LLC - Software Engineer.pdf'."""
    stem = Path(filename).stem
    if " - " in stem:
        return stem.split(" - ", 1)[1].strip()
    return "Unknown Role"
