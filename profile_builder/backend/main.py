"""
Profile Builder API.
Run: uvicorn main:app --reload --port 8000

Endpoints:
  POST /profile/save          -> save (create/update) a profile, returns errors if invalid
  GET  /profile/{profile_id}  -> load a saved profile
  GET  /profile                -> list all saved profile ids + names
"""
import json
import os
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Union

from schema import validate_profile, empty_profile, normalize_confidence

app = FastAPI(title="RADIX Profile Builder API")

# Allow the React dev server to call this API during the hackathon
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PROFILES_DIR = os.path.join(os.path.dirname(__file__), "profiles")
os.makedirs(PROFILES_DIR, exist_ok=True)


class Skill(BaseModel):
    skill_name: str
    category_code: str
    evidence: Optional[str] = ""
    confidence: Optional[Union[int, str]] = None


class Profile(BaseModel):
    profile_id: Optional[str] = None   # if omitted, derived from email
    name: str
    email: str
    education: Optional[str] = ""
    skills: List[Skill] = []
    hackathons: List[str] = []
    internships: List[str] = []
    certifications: List[str] = []
    preferred_roles: List[str] = []
    cv_file: Optional[str] = ""


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "candidate"


def profile_path(profile_id: str) -> str:
    return os.path.join(PROFILES_DIR, f"{profile_id}.json")


@app.post("/profile/save")
def save_profile(profile: Profile):
    profile_id = profile.profile_id or slugify(profile.email or profile.name)
    data = profile.dict(exclude={"profile_id"})

    is_valid, errors = validate_profile(data)
    if not is_valid:
        raise HTTPException(status_code=422, detail={"errors": errors})

    with open(profile_path(profile_id), "w") as f:
        json.dump(data, f, indent=2)

    return {"profile_id": profile_id, "saved": True, "profile": data}


@app.get("/profile/{profile_id}")
def load_profile(profile_id: str):
    path = profile_path(profile_id)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="profile not found")
    with open(path, "r") as f:
        data = json.load(f)

    if isinstance(data.get("skills"), list):
        for s in data["skills"]:
            if isinstance(s, dict):
                s["confidence"] = normalize_confidence(s.get("confidence"))

    return data


@app.get("/profile")
def list_profiles():
    out = []
    for fname in os.listdir(PROFILES_DIR):
        if fname.endswith(".json"):
            profile_id = fname[:-5]
            with open(os.path.join(PROFILES_DIR, fname)) as f:
                data = json.load(f)
            out.append({"profile_id": profile_id, "name": data.get("name", "")})
    return out


@app.get("/profile/new/blank")
def blank_profile():
    return empty_profile()
