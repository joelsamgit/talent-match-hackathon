"""
section_mapper.py — Heuristic section grouping (no LLM call).

Scores each line as a likely section header using:
  - Larger-than-body font size
  - Bold weight
  - ALL-CAPS text
  - Fuzzy keyword match against broad synonym sets per section

Groups lines under their nearest header. If no structure is detected,
returns a single "full_document" section rather than failing.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Optional

from extraction import TextLine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Section keyword synonyms — broad enough to handle format variation
# ---------------------------------------------------------------------------
SECTION_SYNONYMS: dict[str, list[str]] = {
    "skills": [
        "skills", "technical skills", "core competencies", "technologies",
        "tech stack", "tools", "proficiencies", "areas of expertise",
        "programming languages", "frameworks", "technical proficiency",
        "competencies", "key skills", "skill set", "technical expertise",
    ],
    "experience": [
        "experience", "work experience", "work history", "employment",
        "employment history", "professional experience", "career history",
        "internships", "internship experience", "professional background",
        "relevant experience",
    ],
    "education": [
        "education", "academic background", "academic qualifications",
        "educational background", "qualifications", "academic history",
        "degrees", "coursework", "relevant coursework",
    ],
    "projects": [
        "projects", "personal projects", "academic projects",
        "side projects", "key projects", "notable projects",
        "project experience", "selected projects",
    ],
    "certifications": [
        "certifications", "certificates", "licenses", "credentials",
        "professional certifications", "accreditations",
        "courses", "training", "professional development",
    ],
    "summary": [
        "summary", "objective", "profile", "about me", "about",
        "professional summary", "career objective", "personal statement",
        "overview",
    ],
    "contact": [
        "contact", "contact information", "personal information",
        "personal details", "contact details",
    ],
    "achievements": [
        "achievements", "awards", "honors", "accomplishments",
        "recognition", "honours",
    ],
    "publications": [
        "publications", "research", "papers", "research papers",
        "journal articles",
    ],
    "languages": [
        "languages", "language proficiency", "spoken languages",
    ],
    "references": [
        "references",
    ],
}


# ---------------------------------------------------------------------------
# Header-scoring logic
# ---------------------------------------------------------------------------

@dataclass
class _ScoredLine:
    """Internal helper: a line with its header-likelihood score."""
    line: TextLine
    index: int
    score: float = 0.0
    matched_section: Optional[str] = None


def _fuzzy_match_section(text: str) -> tuple[Optional[str], float]:
    """
    Check if `text` fuzzy-matches any known section synonym.

    Returns (section_name, best_similarity_ratio) or (None, 0.0).
    """
    cleaned = re.sub(r"[^a-z\s]", "", text.lower()).strip()
    if not cleaned:
        return None, 0.0

    best_section: Optional[str] = None
    best_ratio = 0.0

    for section, synonyms in SECTION_SYNONYMS.items():
        for syn in synonyms:
            ratio = SequenceMatcher(None, cleaned, syn).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_section = section
            # Also check if the synonym is a prefix/suffix of the cleaned text
            if cleaned.startswith(syn) or cleaned.endswith(syn):
                prefix_ratio = max(ratio, 0.85)
                if prefix_ratio > best_ratio:
                    best_ratio = prefix_ratio
                    best_section = section

    return (best_section, best_ratio) if best_ratio >= 0.65 else (None, 0.0)


def _compute_median_font_size(lines: list[TextLine]) -> float:
    """Compute the median font size across all lines (body text baseline)."""
    sizes = sorted(ln.font_size for ln in lines if ln.font_size and ln.font_size > 0)
    if not sizes:
        return 0.0
    mid = len(sizes) // 2
    return sizes[mid]


def _score_as_header(line: TextLine, median_font: float) -> tuple[float, Optional[str]]:
    """
    Score a single line's likelihood of being a section header.

    Returns (score, matched_section_name).
    Higher score → more likely a header. Threshold applied by the caller.
    """
    text = line.text.strip()
    if not text or len(text) > 80:
        # Very long lines are almost never headers
        return 0.0, None

    score = 0.0

    # 1. Font size larger than body median
    if line.font_size and median_font > 0 and line.font_size > median_font * 1.15:
        score += 2.0

    # 2. Bold weight
    if line.is_bold:
        score += 1.5

    # 3. ALL-CAPS (only meaningful for short lines)
    alpha_chars = [c for c in text if c.isalpha()]
    if alpha_chars and len(alpha_chars) <= 40 and all(c.isupper() for c in alpha_chars):
        score += 1.0

    # 4. Keyword match
    section, ratio = _fuzzy_match_section(text)
    if section:
        score += 2.0 * ratio  # up to +2.0
    
    # 5. Short line bonus (headers are usually short)
    if len(text) <= 30:
        score += 0.5

    return score, section


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_HEADER_THRESHOLD = 2.5  # Minimum score to classify a line as a header


def map_sections(lines: list[TextLine]) -> dict[str, str]:
    """
    Group lines into sections based on heuristic header detection.

    Returns a dict mapping section names (e.g. "skills", "experience")
    to their text blocks. If no headers are detected, returns a single
    {"full_document": <all text>} entry.
    """
    if not lines:
        return {"full_document": ""}

    median_font = _compute_median_font_size(lines)

    # Score every line
    scored: list[_ScoredLine] = []
    for i, ln in enumerate(lines):
        s, sec = _score_as_header(ln, median_font)
        scored.append(_ScoredLine(line=ln, index=i, score=s, matched_section=sec))

    # Identify header lines (score above threshold)
    headers = [(sl.index, sl.matched_section or _normalize_label(sl.line.text), sl.line.text)
               for sl in scored if sl.score >= _HEADER_THRESHOLD]

    if not headers:
        # No structure detected — return everything as one block
        full = "\n".join(ln.text for ln in lines)
        return {"full_document": full}

    # Build section text blocks
    sections: dict[str, str] = {}
    for pos, (hdr_idx, section_name, _raw) in enumerate(headers):
        # The section body runs from the line after this header
        # to the line before the next header (or end of document)
        start = hdr_idx + 1
        end = headers[pos + 1][0] if pos + 1 < len(headers) else len(lines)

        body_lines = [lines[j].text for j in range(start, end)]
        body = "\n".join(body_lines).strip()

        # If the same section name appears twice, merge
        if section_name in sections:
            sections[section_name] += "\n" + body
        else:
            sections[section_name] = body

    # Capture any text before the first header as "preamble"
    first_hdr_idx = headers[0][0]
    if first_hdr_idx > 0:
        preamble = "\n".join(lines[j].text for j in range(first_hdr_idx)).strip()
        if preamble:
            sections["preamble"] = preamble

    return sections


def _normalize_label(text: str) -> str:
    """Normalize a raw header line into a clean section label."""
    cleaned = re.sub(r"[^a-zA-Z\s]", "", text).strip().lower()
    # Collapse whitespace
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned or "unknown"
