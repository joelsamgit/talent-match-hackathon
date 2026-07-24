# Role 5: Skill Matching

> **RADIX Talent Match Hackathon** — Module owned by: **Role 5**

---

## What It Does

This module is a Python + FastAPI REST API for **Role 5: Skill Matching**. It accepts structured outputs from Role 1 (JD Analytics) and Role 2 / Role 3 (Candidate Resume / Profile), performs **semantic fuzzy skill matching** using the **Groq API (`llama-3.3-70b-versatile`)**, calculates a weighted **Match Score (0–100)**, details matched skills with evidence, and prioritizes missing skill gaps.

---

## Setup

```bash
# 1. Navigate into this folder
cd skill_matching

# 2. Create and activate a virtual environment
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows (PowerShell)
venv\Scripts\Activate.ps1

# Windows (CMD)
venv\Scripts\activate.bat

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure your API key
cp .env.example .env
# Open .env and set: GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxx
# Free key at: https://console.groq.com → API Keys (no credit card needed)

# 5. Start the server
uvicorn main:app --reload --port 8005
```

Server runs at: **http://localhost:8005**  
Interactive Swagger docs: **http://localhost:8005/docs**

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | ✅ Yes | Your Groq API key. Get one free at [console.groq.com](https://console.groq.com) |
| `PORT` | No | Override the port (default: `8005`) |

> ⚠️ **Never commit `.env`** — it is gitignored. Only `.env.example` (with placeholder values) is committed.

---

## API Endpoints

### `GET /health`
Liveness check. Returns `200 OK` if the service is running.

**curl:**
```bash
curl http://localhost:8005/health
```

---

### `GET /samples`
Lists available sample JDs and sample candidate profiles for testing.

**curl:**
```bash
curl http://localhost:8005/samples
```

---

### `POST /match`
Perform semantic skill matching between JD Analytics output and Candidate Profile.

**Request Body (JSON):**
```json
{
  "jd_analytics": {
    "source_type": "jd",
    "source_file": "Google LLC - Software Engineer.pdf",
    "company": "Google LLC",
    "role": "Software Engineer",
    "skills": [
      {
        "skill_name": "Data Structures & Algorithms",
        "category_code": "DSA"
      }
    ]
  },
  "candidate_profile": {
    "candidate_name": "Ananya Rao",
    "skills": [
      {
        "skill_name": "Data Structures & Algorithms (350+ LeetCode problems)",
        "category_code": "DSA"
      }
    ]
  }
}
```

**curl:**
```bash
curl -X POST http://localhost:8005/match \
  -H "Content-Type: application/json" \
  -d '{"jd_analytics": {...}, "candidate_profile": {...}}'
```

---

### `POST /match-sample`
Evaluate matching for any sample JD and sample Candidate pair.

**curl:**
```bash
curl -X POST http://localhost:8005/match-sample \
  -H "Content-Type: application/json" \
  -d '{"jd_filename": "Google LLC - Software Engineer.pdf", "candidate_name": "Ananya Rao"}'
```

---

## Shared Data Contract (Output Schema)

```json
{
  "jd_source_file": "Google LLC - Software Engineer.pdf",
  "company": "Google LLC",
  "role": "Software Engineer (SWE)",
  "candidate_name": "Ananya Rao",
  "match_score": 85,
  "summary": "Strong candidate for backend/systems software engineering with robust DSA, OS, and System Design background.",
  "matched_skills": [
    {
      "jd_skill_name": "Data Structures & Algorithms",
      "category_code": "DSA",
      "candidate_skill_name": "Data Structures & Algorithms (350+ competitive programming problems)",
      "match_confidence": "high",
      "explanation": "Candidate has extensive competitive programming practice in DSA."
    }
  ],
  "missing_skills": [
    {
      "jd_skill_name": "Cloud Infrastructure",
      "category_code": "SYSD",
      "importance": "medium",
      "explanation": "No formal AWS/GCP/Azure experience listed on candidate profile."
    }
  ]
}
```

---

## Folder Structure

```
skill_matching/
├── main.py              # FastAPI app & endpoints
├── matcher.py           # LLM semantic matching engine (Groq)
├── scoring.py           # Match score calculation & fallback fuzzy logic
├── models.py            # Pydantic models (data contract)
├── requirements.txt     # Dependencies
├── .env.example         # GROQ_API_KEY=your_key_here
├── .gitignore           # Git ignore rules
├── README.md            # API documentation & setup instructions
└── tests/               # Pytest suite
```
