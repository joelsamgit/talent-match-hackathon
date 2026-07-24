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


MODEL = "llama-3.3-70b-versatile"

# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

_CATEGORY_LIST = "\n".join(
    f'  - "{code}": {desc}'
    for code, desc in CATEGORY_DESCRIPTIONS.items()
)

SYSTEM_PROMPT = f"""You are an expert technical recruiter and skills analyst.

Your task is to analyze a Job Description (JD) and extract all the skills, competencies,
and requirements mentioned — then map each one to exactly one of the 12 RADIX skill categories.

## The 12 RADIX Categories (use ONLY these codes):
{_CATEGORY_LIST}

## Rules:
1. Extract every distinct skill, tool, or competency mentioned in the JD.
2. Map each to exactly ONE category code from the list above.
3. Provide a short verbatim quote (≤ 30 words) from the JD as "evidence".
4. Set "confidence" to:
   - "high"   → explicitly stated requirement
   - "medium" → strongly implied or mentioned as preferred
   - "low"    → background expectation or inferred from context
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
      "category_code": "<one of the 12 codes>",
      "evidence": "<short verbatim quote from JD>",
      "confidence": "<high|medium|low>"
    }}
  ]
}}

## Few-shot examples of correct skill extractions:

Example 1 — from a Google Software Engineer JD:
{{
  "skill_name": "Data Structures & Algorithms",
  "category_code": "DSA",
  "evidence": "Strong grasp of data structures, algorithms, and complexity analysis",
  "confidence": "high"
}}

Example 2 — from a Microsoft Data Analyst JD:
{{
  "skill_name": "SQL & Database Querying",
  "category_code": "DB",
  "evidence": "Write complex SQL queries to extract and manipulate data from relational databases",
  "confidence": "high"
}}

Example 3 — from an Oracle JD:
{{
  "skill_name": "Communication & Stakeholder Management",
  "category_code": "COMM",
  "evidence": "Excellent written and verbal communication skills to liaise with clients",
  "confidence": "high"
}}
"""


def _build_user_message(jd_text: str) -> str:
    return f"""Analyze the following Job Description and extract all skills.
Return ONLY the JSON object described in your instructions.

--- JD TEXT START ---
{jd_text}
--- JD TEXT END ---
"""


# ---------------------------------------------------------------------------
# Core analysis function
# ---------------------------------------------------------------------------

def analyze_jd(text: str, filename: str = "unknown.txt") -> JDAnalyticsOutput:
    """
    Send JD text to Groq and return a validated JDAnalyticsOutput.

    Args:
        text:     Plain text extracted from the JD file.
        filename: Original filename (for source_file field).

    Returns:
        Validated JDAnalyticsOutput instance.

    Raises:
        RuntimeError: On API or parsing failures.
    """
    if not text or not text.strip():
        raise ValueError("JD text is empty — cannot analyze an empty document.")

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
                {"role": "user", "content": _build_user_message(text)},
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
        # Gracefully handle any hallucinated codes
        if code not in valid_codes:
            code = _fuzzy_match_code(code, valid_codes)

        confidence_raw = item.get("confidence", "high").lower()
        try:
            confidence = ConfidenceLevel(confidence_raw)
        except ValueError:
            confidence = ConfidenceLevel.MEDIUM

        skills.append(
            SkillObject(
                skill_name=item.get("skill_name", "Unknown Skill"),
                category_code=CategoryCode(code),
                evidence=item.get("evidence", ""),
                confidence=confidence,
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
