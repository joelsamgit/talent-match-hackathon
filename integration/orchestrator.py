"""
orchestrator.py — Unified pipeline orchestrator for RADIX Talent Match.

Exposes:
  - run_jd_analytics(jd_file_path) -> dict
  - run_resume_parsing(resume_file_path) -> dict
  - run_talent_check(profile, company) -> dict
  - run_skill_match(profile, jd_skills) -> dict
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv

_INTEGRATION_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _INTEGRATION_DIR.parent

_JD_ANALYTICS_DIR = _REPO_ROOT / "JD Analytics"
_RESUME_PARS_DIR = _REPO_ROOT / "resume_pars"
_PROFILE_BUILDER_DIR = _REPO_ROOT / "profile_builder" / "backend"
_TALENT_CHECK_DIR = _REPO_ROOT / "talent_check"
_SKILL_MATCHING_DIR = _REPO_ROOT / "skill_matching"

# Load environment variables
load_dotenv(_JD_ANALYTICS_DIR / ".env", override=True)
load_dotenv(_RESUME_PARS_DIR / ".env", override=True)
load_dotenv(_SKILL_MATCHING_DIR / ".env", override=True)


def _activate_module_path(target_dir: Path, extra_dirs: list[Path] = None):
    """Isolate sys.path for the target module directory so local files (e.g. models.py) don't conflict."""
    all_teammate_dirs = [
        str(_JD_ANALYTICS_DIR),
        str(_RESUME_PARS_DIR),
        str(_RESUME_PARS_DIR / "routers"),
        str(_PROFILE_BUILDER_DIR),
        str(_TALENT_CHECK_DIR),
        str(_SKILL_MATCHING_DIR),
    ]
    for d in all_teammate_dirs:
        if d in sys.path:
            sys.path.remove(d)

    # Purge shadowed modules — include ALL possible names from any teammate folder
    _purge_names = (
        "models", "schema", "analyzer", "extractor", "extraction",
        "matcher", "scoring", "resume_parsing", "llm_client",
        "section_mapper", "talent_check", "main",
    )
    to_remove = []
    for name in list(sys.modules.keys()):
        basename = name.split(".")[0]
        if basename in _purge_names:
            to_remove.append(name)
    for name in to_remove:
        sys.modules.pop(name, None)

    if extra_dirs:
        for ed in extra_dirs:
            sys.path.insert(0, str(ed))
    sys.path.insert(0, str(target_dir))


def run_jd_analytics(jd_file_path: str) -> Dict[str, Any]:
    """
    Extract text from a JD file (.txt, .pdf, .docx) and run Groq skill analytics.
    """
    path = Path(jd_file_path)
    if not path.exists():
        raise FileNotFoundError(f"JD file not found: {jd_file_path}")

    _activate_module_path(_JD_ANALYTICS_DIR)
    import analyzer
    import extractor

    filename = path.name
    suffix = path.suffix.lower()

    if suffix in (".txt", ".md"):
        text = path.read_text(encoding="utf-8", errors="ignore")
    else:
        file_bytes = path.read_bytes()
        text = extractor.extract_text(filename, file_bytes)

    analysis = analyzer.analyze_jd(text, filename=filename)
    return analysis.model_dump()


def run_resume_parsing(resume_file_path: str) -> Dict[str, Any]:
    """
    Parse a resume file (.pdf, .docx) and return structured skills & biographical fields.
    """
    path = Path(resume_file_path)
    if not path.exists():
        raise FileNotFoundError(f"Resume file not found: {resume_file_path}")

    _activate_module_path(_RESUME_PARS_DIR, extra_dirs=[_RESUME_PARS_DIR / "routers"])
    import resume_parsing

    return resume_parsing.parse_resume_file(str(path))


def run_talent_check(profile: Dict[str, Any], company: str) -> Dict[str, Any]:
    """
    Benchmark candidate profile skill levels against company requirements.
    """
    _activate_module_path(_TALENT_CHECK_DIR)
    import talent_check

    benchmarks_path = _TALENT_CHECK_DIR / "talent_check_company_skillsets.json"
    if not benchmarks_path.exists():
        raise FileNotFoundError("Company benchmarks JSON missing.")

    with open(benchmarks_path, "r", encoding="utf-8") as f:
        company_benchmarks = json.load(f)

    return talent_check.calculate_talent_check(company, profile, company_benchmarks)


def run_skill_match(profile: Dict[str, Any], jd_skills: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform semantic skill matching between candidate profile and JD analytics output.
    """
    _activate_module_path(_SKILL_MATCHING_DIR)
    import matcher

    result = matcher.match_candidate_to_jd(jd_skills, profile)
    return result.model_dump()
