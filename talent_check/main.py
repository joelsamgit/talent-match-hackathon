import json
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any

from talent_check import calculate_talent_check

app = FastAPI(title="RADIX Talent Check API (Role 4)")

# Allow the frontend to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the company benchmarks into memory on startup
BENCHMARKS_FILE = os.path.join(os.path.dirname(__file__), "talent_check_company_skillsets.json")
try:
    with open(BENCHMARKS_FILE, "r") as f:
        COMPANY_BENCHMARKS = json.load(f)
except FileNotFoundError:
    COMPANY_BENCHMARKS = {}

# Define the expected incoming JSON format
class TalentCheckRequest(BaseModel):
    company_name: str
    candidate_profile: Dict[str, Any]

@app.post("/talent-check")
def run_talent_check(payload: TalentCheckRequest):
    if not COMPANY_BENCHMARKS:
        raise HTTPException(status_code=500, detail="Company benchmark data file is missing.")
        
    result = calculate_talent_check(
        company_name=payload.company_name,
        candidate_profile=payload.candidate_profile,
        company_benchmarks=COMPANY_BENCHMARKS
    )
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
        
    return result