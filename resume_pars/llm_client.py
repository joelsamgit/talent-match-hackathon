"""
llm_client.py — LLM calling module with provider fallback chain.

Implements:
  - Skill extraction (Stage 3) with chunking for long resumes
  - Structured field extraction (Stage 4) against full text
  - Provider fallback chain (Stage 5): Groq → Gemini
  - Schema validation + single retry (Stage 6)

Both Groq and Gemini are called via their official SDKs with native
JSON-mode to reduce retry rates. All calls go through a shared
`_call_llm()` function that handles the fallback chain.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Optional

from pydantic import ValidationError

from schema import Skill, StructuredFields, ProjectEntry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider configuration
# ---------------------------------------------------------------------------
GROQ_MODEL = "llama-3.3-70b-versatile"
GEMINI_MODEL = "gemini-2.0-flash"

# Rough word budget before we chunk (3000 words ≈ ~4000 tokens)
_MAX_WORDS_SINGLE_CALL = 3000


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

SKILL_SYSTEM_PROMPT = """You are a precise information-extraction engine. Your only job is to read \
resume text and extract the technical and professional skills it evidences, mapped to a fixed set \
of category codes. You do not evaluate the candidate, you do not add commentary, and you do not \
infer skills that are not reasonably evidenced by the text.

CATEGORY CODES (use exactly one per skill):
DSA: data structures & algorithms
COD: general coding/programming ability, languages
OOD: object-oriented design/architecture
APTI: quantitative/logical aptitude
COMM: communication, collaboration, leadership
AI: artificial intelligence, machine learning, LLMs
CLOUD: cloud platforms, deployment, infrastructure
SQL: databases, query languages, data modeling
SWE: general software engineering practice (testing, version control, CI/CD)
SYSD: system design, architecture at scale
NETW: networking
OS: operating systems, low-level systems programming
OTHER: any real technical/professional skill that doesn't fit above

RULES:
1. Evidence must come from what the candidate did (skills, tools, actions, outcomes) — never from a summary tagline, job title, or preferred-roles list. Do not cite phrases like "strong fit for X roles" or a candidate's listed job-title preferences as evidence — only cite descriptions of actual work, tools used, or outcomes achieved.
2. Every skill must have a short "evidence" string (under 10 words) quoted or paraphrased from the text. Never output a skill with no textual basis.
3. confidence: "high" if explicitly stated, "medium" if reasonably implied, "low" if only weakly suggested, and always "low" if the source text came from OCR and the relevant phrase looks garbled or uncertain.
4. Do not invent skills. Sparse text should produce fewer skills, not padded ones.
5. Do not duplicate the same skill under two categories.
6. Output ONLY valid JSON matching the schema. No prose, no markdown fences.
7. Before finalizing output, cross-check every item explicitly listed in a "Skills" or "Technical Skills" section — each should appear in your output unless genuinely too vague to map to a category.

OUTPUT SCHEMA:
{"skills": [{"skill_name": str, "category_code": str, "evidence": str, "confidence": str}]}"""

STRUCTURED_FIELDS_SYSTEM_PROMPT = """You are a precise information-extraction engine. Extract structured \
biographical and educational fields from resume text. Do not extract skills here. Do not infer \
information not present in the text — return null for missing fields rather than guessing. \
Normalize dates to "MMM YYYY" or "YYYY" if only a year is given. Output ONLY valid JSON matching \
the StructuredFields schema. No prose, no markdown fences.

OUTPUT SCHEMA:
{
  "name": str or null,
  "email": str or null,
  "education": str or null,
  "experience_years_estimate": number or null,
  "projects": [{"title": str, "description": str}],
  "internships": [str],
  "certifications": [str]
}"""


# ---------------------------------------------------------------------------
# Few-shot examples for skill extraction
# ---------------------------------------------------------------------------

_SKILL_FEW_SHOT = [
    {
        "role": "user",
        "content": "Built and deployed a microservices-based inventory system on AWS using Docker and Kubernetes; wrote unit and integration tests achieving 90% coverage; mentored two junior engineers.",
    },
    {
        "role": "assistant",
        "content": json.dumps({
            "skills": [
                {"skill_name": "Microservices architecture", "category_code": "SYSD", "evidence": "microservices-based inventory system", "confidence": "high"},
                {"skill_name": "AWS", "category_code": "CLOUD", "evidence": "deployed ... on AWS", "confidence": "high"},
                {"skill_name": "Docker", "category_code": "CLOUD", "evidence": "using Docker and Kubernetes", "confidence": "high"},
                {"skill_name": "Kubernetes", "category_code": "CLOUD", "evidence": "using Docker and Kubernetes", "confidence": "high"},
                {"skill_name": "Automated testing", "category_code": "SWE", "evidence": "unit and integration tests, 90% coverage", "confidence": "high"},
                {"skill_name": "Mentorship/leadership", "category_code": "COMM", "evidence": "mentored two junior engineers", "confidence": "medium"},
            ]
        }),
    },
    {
        "role": "user",
        "content": "SQL (basic), Java, Linux basics, exposure to ticketing tools.",
    },
    {
        "role": "assistant",
        "content": json.dumps({
            "skills": [
                {"skill_name": "SQL", "category_code": "SQL", "evidence": "SQL (basic)", "confidence": "low"},
                {"skill_name": "Java", "category_code": "COD", "evidence": "Java", "confidence": "medium"},
                {"skill_name": "Linux fundamentals", "category_code": "OS", "evidence": "Linux basics", "confidence": "low"},
                {"skill_name": "IT support/ticketing", "category_code": "OTHER", "evidence": "exposure to ticketing tools", "confidence": "low"},
            ]
        }),
    },
    {
        "role": "user",
        "content": "Built an end-to-end churn-prediction pipeline (SQL extraction, feature engineering, logistic regression) and ran an A/B test simulation comparing two onboarding flows, presenting results to a non-technical audience.",
    },
    {
        "role": "assistant",
        "content": json.dumps({
            "skills": [
                {"skill_name": "SQL data extraction", "category_code": "SQL", "evidence": "SQL extraction", "confidence": "high"},
                {"skill_name": "Machine learning modeling", "category_code": "AI", "evidence": "logistic regression, feature engineering", "confidence": "high"},
                {"skill_name": "A/B testing", "category_code": "APTI", "evidence": "A/B test simulation", "confidence": "medium"},
                {"skill_name": "Stakeholder communication", "category_code": "COMM", "evidence": "presenting results to a non-technical audience", "confidence": "medium"},
            ]
        }),
    },
]


# ---------------------------------------------------------------------------
# Provider backends
# ---------------------------------------------------------------------------

def _call_groq(
    system_prompt: str,
    user_content: str,
    prior_messages: list[dict] | None = None,
) -> tuple[str, bool]:
    """
    Call Groq (llama-3.3-70b-versatile) with JSON mode.

    Returns (response_text, success). On any failure returns ("", False).
    """
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        logger.warning("GROQ_API_KEY not set — skipping Groq provider.")
        return "", False

    try:
        from groq import Groq

        client = Groq(api_key=api_key)
        messages = [{"role": "system", "content": system_prompt}]
        if prior_messages:
            messages.extend(prior_messages)
        messages.append({"role": "user", "content": user_content})

        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=4096,
        )
        text = response.choices[0].message.content or ""
        logger.info("Groq responded (%d chars)", len(text))
        return text, True

    except Exception as exc:
        logger.warning("Groq call failed: %s", exc)
        return "", False


def _call_gemini(
    system_prompt: str,
    user_content: str,
    prior_messages: list[dict] | None = None,
) -> tuple[str, bool]:
    """
    Call Gemini (gemini-2.0-flash) with JSON mode as fallback.

    Returns (response_text, success). On any failure returns ("", False).
    """
    api_key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        logger.warning("GEMINI_API_KEY / GOOGLE_API_KEY not set — skipping Gemini provider.")
        return "", False

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)

        # Build the prompt: system instruction + few-shot examples + user content
        # Gemini's chat format doesn't map 1:1 to OpenAI-style messages,
        # so we flatten few-shot examples into the prompt.
        full_prompt_parts = []
        if prior_messages:
            for msg in prior_messages:
                role_label = "User" if msg["role"] == "user" else "Assistant"
                full_prompt_parts.append(f"{role_label}: {msg['content']}")
            full_prompt_parts.append("")  # blank separator
        full_prompt_parts.append(user_content)
        combined_prompt = "\n".join(full_prompt_parts)

        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=system_prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1,
                max_output_tokens=4096,
            ),
        )

        response = model.generate_content(combined_prompt)
        text = response.text or ""
        logger.info("Gemini responded (%d chars)", len(text))
        return text, True

    except Exception as exc:
        logger.warning("Gemini call failed: %s", exc)
        return "", False


# ---------------------------------------------------------------------------
# Shared LLM calling function with fallback + retry
# ---------------------------------------------------------------------------

def _clean_json_response(text: str) -> str:
    """Strip markdown fences and leading/trailing whitespace from LLM output."""
    text = text.strip()
    # Remove ```json ... ``` wrappers
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _call_llm(
    system_prompt: str,
    user_content: str,
    prior_messages: list[dict] | None = None,
) -> tuple[str, str]:
    """
    Shared LLM calling function with provider fallback chain.

    Tries Groq first, then Gemini. Returns (response_text, provider_name).
    If all providers fail, returns ("", "none").
    """
    providers = [
        ("groq", _call_groq),
        ("gemini", _call_gemini),
    ]

    for provider_name, call_fn in providers:
        text, ok = call_fn(system_prompt, user_content, prior_messages)
        if ok and text.strip():
            return _clean_json_response(text), provider_name

    return "", "none"


def _call_llm_with_validation(
    system_prompt: str,
    user_content: str,
    parse_fn,
    prior_messages: list[dict] | None = None,
) -> tuple[Any, str, list[str]]:
    """
    Call the LLM, validate the response, and retry once on failure.

    Args:
        system_prompt: The system prompt for the LLM.
        user_content: The user content (resume text).
        parse_fn: A callable that takes the raw JSON string and returns a
                  parsed object. Should raise ValueError/ValidationError on bad data.
        prior_messages: Optional few-shot examples.

    Returns:
        (parsed_result, provider_name, warnings)
    """
    warnings: list[str] = []

    # First attempt
    raw, provider = _call_llm(system_prompt, user_content, prior_messages)
    if not raw:
        warnings.append("All LLM providers failed to return a response.")
        return None, "none", warnings

    try:
        result = parse_fn(raw)
        logger.info("LLM response validated on first attempt (provider=%s)", provider)
        return result, provider, warnings
    except (json.JSONDecodeError, ValidationError, ValueError, KeyError, TypeError) as exc:
        error_msg = str(exc)
        logger.warning("First LLM response invalid: %s", error_msg)

    # Retry once with the error feedback
    retry_prompt = (
        f"Your previous response was not valid JSON matching the required schema. "
        f"The validation error was: {error_msg}. "
        f"Return ONLY the corrected JSON object."
    )
    retry_content = f"{user_content}\n\n{retry_prompt}"
    raw_retry, provider_retry = _call_llm(system_prompt, retry_content, prior_messages)

    if raw_retry:
        try:
            result = parse_fn(raw_retry)
            logger.info("LLM response validated on retry (provider=%s)", provider_retry)
            warnings.append(f"Initial LLM response was invalid; succeeded on retry via {provider_retry}.")
            return result, provider_retry, warnings
        except (json.JSONDecodeError, ValidationError, ValueError, KeyError, TypeError) as exc2:
            logger.error("Retry also failed: %s", exc2)
            warnings.append(f"LLM validation failed after retry: {exc2}")

    warnings.append("All LLM attempts failed schema validation.")
    return None, provider, warnings


# ---------------------------------------------------------------------------
# Stage 3 — Skill extraction
# ---------------------------------------------------------------------------

def _parse_skills_response(raw_json: str) -> list[Skill]:
    """Parse and validate the raw JSON from the skill-extraction LLM call."""
    data = json.loads(raw_json)
    skills_raw = data.get("skills", [])
    if not isinstance(skills_raw, list):
        raise ValueError(f"Expected 'skills' to be a list, got {type(skills_raw)}")

    validated: list[Skill] = []
    for item in skills_raw:
        validated.append(Skill(**item))

    return validated


def _split_into_chunks(
    full_text: str,
    sections: dict[str, str],
    max_words: int = _MAX_WORDS_SINGLE_CALL,
) -> list[str]:
    """
    Split resume text into chunks that fit within the token budget.

    Prefers splitting at section boundaries. If sections aren't available,
    falls back to splitting by paragraph breaks.
    """
    word_count = len(full_text.split())
    if word_count <= max_words:
        return [full_text]

    # Try section-based chunks
    if sections and "full_document" not in sections:
        chunks: list[str] = []
        current_chunk: list[str] = []
        current_words = 0

        for section_name, body in sections.items():
            section_text = f"[{section_name.upper()}]\n{body}"
            section_words = len(section_text.split())

            if current_words + section_words > max_words and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_words = 0

            current_chunk.append(section_text)
            current_words += section_words

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        if chunks:
            return chunks

    # Fallback: split by paragraphs
    paragraphs = full_text.split("\n\n")
    chunks = []
    current_chunk = []
    current_words = 0

    for para in paragraphs:
        para_words = len(para.split())
        if current_words + para_words > max_words and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = []
            current_words = 0
        current_chunk.append(para)
        current_words += para_words

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    # If paragraph splitting still left oversized chunks (e.g. no \n\n in text),
    # do a hard word-count split as a last resort
    final_chunks: list[str] = []
    for chunk in (chunks or [full_text]):
        words = chunk.split()
        if len(words) <= max_words:
            final_chunks.append(chunk)
        else:
            for start in range(0, len(words), max_words):
                final_chunks.append(" ".join(words[start : start + max_words]))

    return final_chunks or [full_text]


def _dedupe_skills(skills: list[Skill]) -> list[Skill]:
    """Deduplicate skills by (skill_name_lower, category_code), keeping higher confidence."""
    confidence_rank = {"high": 3, "medium": 2, "low": 1}
    seen: dict[tuple[str, str], Skill] = {}

    for skill in skills:
        key = (skill.skill_name.lower().strip(), skill.category_code)
        existing = seen.get(key)
        if existing is None:
            seen[key] = skill
        else:
            # Keep the one with higher confidence
            if confidence_rank.get(skill.confidence, 0) > confidence_rank.get(existing.confidence, 0):
                seen[key] = skill

    return list(seen.values())


def extract_skills(
    full_text: str,
    sections: dict[str, str] | None = None,
    is_ocr: bool = False,
) -> tuple[list[Skill], list[str]]:
    """
    Extract skills from resume text using LLM with chunking if needed.

    Args:
        full_text: The complete resume text.
        sections: Optional section mapping from section_mapper.
        is_ocr: Whether the text was obtained via OCR (affects confidence).

    Returns:
        (list_of_skills, warnings)
    """
    if not full_text.strip():
        return [], ["No text provided for skill extraction."]

    warnings: list[str] = []
    all_skills: list[Skill] = []

    chunks = _split_into_chunks(full_text, sections or {})
    logger.info("Skill extraction: %d chunk(s)", len(chunks))

    for i, chunk in enumerate(chunks):
        user_content = chunk
        if is_ocr:
            user_content = "[NOTE: This text was extracted via OCR and may contain errors.]\n\n" + chunk

        result, provider, chunk_warnings = _call_llm_with_validation(
            system_prompt=SKILL_SYSTEM_PROMPT,
            user_content=user_content,
            parse_fn=_parse_skills_response,
            prior_messages=_SKILL_FEW_SHOT,
        )
        warnings.extend(chunk_warnings)

        if result is not None:
            all_skills.extend(result)
            logger.info("Chunk %d/%d: %d skills extracted via %s", i + 1, len(chunks), len(result), provider)
        else:
            warnings.append(f"Skill extraction failed for chunk {i + 1}/{len(chunks)}.")

    deduped = _dedupe_skills(all_skills)
    if len(deduped) < len(all_skills):
        logger.info("Deduped %d → %d skills", len(all_skills), len(deduped))

    return deduped, warnings


def verify_skill_coverage(sections: dict[str, str], extracted_skills: list[Skill]) -> list[str]:
    """
    Cross-checks extracted skills against items explicitly listed in a 'skills' section.
    Returns a list of warning strings for likely missed skills.
    """
    warnings = []
    
    # Identify skills sections
    skill_text = ""
    for sec_name, sec_body in sections.items():
        if "skill" in sec_name.lower():
            skill_text += sec_body + "\n"
            
    if not skill_text.strip():
        return warnings
        
    # Basic tokenization of comma/newline/bullet separated items
    raw_tokens = [t.strip() for t in re.split(r'[,;\n\u2022|]', skill_text)]
    
    cleaned_tokens = []
    for t in raw_tokens:
        # Strip prefixes like "Languages:" or "Tools:"
        if ':' in t:
            t = t.split(':', 1)[1].strip()
        t = t.strip(' ()[]*-')
        if len(t) >= 2 and len(t) <= 40:
            cleaned_tokens.append(t)
            
    extracted_lower = [s.skill_name.lower() for s in extracted_skills]
    missed = []
    
    for token in set(cleaned_tokens):
        token_lower = token.lower()
        found = False
        for ext in extracted_lower:
            # Fuzzy inclusion check
            if token_lower in ext or ext in token_lower:
                found = True
                break
        if not found:
            missed.append(token)
            
    if missed:
        warnings.append(f"verify_skill_coverage flagged potential dropped skills: {', '.join(missed)}")
        
    return warnings

# ---------------------------------------------------------------------------
# Stage 4 — Structured field extraction
# ---------------------------------------------------------------------------

def _parse_fields_response(raw_json: str) -> StructuredFields:
    """Parse and validate the raw JSON from the structured-fields LLM call."""
    data = json.loads(raw_json)

    # Normalize projects from raw dicts to ProjectEntry objects
    raw_projects = data.get("projects", [])
    if isinstance(raw_projects, list):
        projects = []
        for p in raw_projects:
            if isinstance(p, dict) and "title" in p:
                projects.append(ProjectEntry(**p))
        data["projects"] = projects
    else:
        data["projects"] = []

    return StructuredFields(**data)


def extract_structured_fields(full_text: str) -> tuple[StructuredFields | None, list[str]]:
    """
    Extract structured biographical fields from the full resume text.

    Always runs against the complete text (not chunked) to preserve context
    for fields like experience_years_estimate that need the full picture.

    Returns:
        (structured_fields, warnings)
    """
    if not full_text.strip():
        return StructuredFields(), ["No text provided for field extraction."]

    result, provider, warnings = _call_llm_with_validation(
        system_prompt=STRUCTURED_FIELDS_SYSTEM_PROMPT,
        user_content=full_text,
        parse_fn=_parse_fields_response,
    )

    if result is not None:
        logger.info("Structured fields extracted via %s", provider)
        return result, warnings

    # All attempts failed — return empty fields with warning
    return StructuredFields(), warnings
