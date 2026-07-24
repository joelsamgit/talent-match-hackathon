# Role 1: JD Analytics

> **RADIX Talent Match Hackathon** — Module owned by: **Role 1**

---

## What It Does

This module is a Python + FastAPI REST API that accepts a Job Description file (PDF or DOCX), extracts its text, and sends it to the **Groq API** (`llama-3.3-70b-versatile`) with an engineered prompt. The LLM maps every skill, competency, and requirement found in the JD to one of the **12 RADIX skill categories** and returns a structured JSON response that other modules (Resume Analyzer, Profile Builder, Matching Engine) consume directly.

---

## Setup

```bash
# 1. Navigate into this folder
cd jd_analytics

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
uvicorn main:app --reload --port 8001
```

Server runs at: **http://localhost:8001**  
Interactive Swagger docs: **http://localhost:8001/docs**

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | ✅ Yes | Your Groq API key. Get one free at [console.groq.com](https://console.groq.com) |
| `PORT` | No | Override the port (default: `8001`) |

> ⚠️ **Never commit `.env`** — it is gitignored. Only `.env.example` (with placeholder values) is committed.

---

## API Endpoints

### `GET /health`
Liveness check. Returns `200 OK` if the server is running.

**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

**curl:**
```bash
curl http://localhost:8001/health
```

---

### `GET /samples`
Lists all bundled sample JD files available for testing via `/analyze-sample`.

**Response:**
```json
{
  "samples": [
    "Google LLC - Software Engineer.pdf",
    "Microsoft - Data Analyst.pdf"
  ],
  "count": 12
}
```

**curl:**
```bash
curl http://localhost:8001/samples
```

---

### `POST /analyze`
Upload a PDF or DOCX job description. Returns the full structured skill extraction.

**Request:** `multipart/form-data` with a `file` field.

**curl:**
```bash
curl -X POST http://localhost:8001/analyze \
  -F "file=@path/to/Google LLC - Software Engineer.pdf"
```

**Response:**
```json
{
  "source_type": "jd",
  "source_file": "Google LLC - Software Engineer.pdf",
  "company": "Google LLC",
  "role": "Software Engineer",
  "raw_text_length": 3240,
  "skills": [
    {
      "skill_name": "Data Structures & Algorithms",
      "category_code": "DSA",
      "evidence": "Strong grasp of data structures and algorithms",
      "confidence": "high"
    },
    {
      "skill_name": "System Design at Scale",
      "category_code": "SYSD",
      "evidence": "Comfort reasoning about system design at scale",
      "confidence": "high"
    }
  ]
}
```

---

### `POST /analyze-text`
Send pre-extracted JD text directly (no file upload needed).  
Used by **Role 3 (Profile Builder)** to pass text without re-uploading.

**Request body (JSON):**
```json
{
  "text": "We are looking for a Software Engineer with strong DSA skills...",
  "filename": "optional_label.txt"
}
```

**curl:**
```bash
curl -X POST http://localhost:8001/analyze-text \
  -H "Content-Type: application/json" \
  -d '{"text": "Strong knowledge of data structures and algorithms required.", "filename": "test.txt"}'
```

**Response:** Same shape as `/analyze`.

---

### `POST /analyze-sample/{filename}`
Analyze a bundled sample JD without uploading anything. Use `GET /samples` to see available filenames.

**curl:**
```bash
# URL-encode spaces as %20
curl -X POST "http://localhost:8001/analyze-sample/Google%20LLC%20-%20Software%20Engineer.pdf"
```

**Response:** Same shape as `/analyze`.

---

## Output Data Contract

All endpoints return the **same JSON shape**. This is the shared contract consumed by other modules.

```json
{
  "source_type": "jd",
  "source_file": "<original filename>",
  "company": "<company name extracted from JD>",
  "role": "<job title extracted from JD>",
  "raw_text_length": 3240,
  "skills": [
    {
      "skill_name": "<human readable skill name>",
      "category_code": "<one of 12 RADIX codes>",
      "evidence": "<short verbatim quote from the JD>",
      "confidence": "high | medium | low"
    }
  ]
}
```

### The 12 RADIX Category Codes

| Code | Category |
|------|----------|
| `DSA` | Data Structures & Algorithms |
| `COD` | Coding Proficiency |
| `OOD` | Object-Oriented Design & Patterns |
| `SYSD` | System Design & Architecture |
| `OS` | Operating Systems |
| `NETW` | Computer Networking |
| `DB` | Databases & SQL |
| `SWE` | Software Engineering Practices |
| `DATA` | Data Science, ML & Analytics |
| `APTI` | Aptitude, Logic & Problem Solving |
| `COMM` | Communication & Collaboration |
| `MGMT` | Project & Product Management |

---

## Project Structure

```
jd_analytics/
├── main.py          # FastAPI app — all routes, CORS, request validation
├── extractor.py     # PDF (pdfplumber) and DOCX (python-docx) text extraction
├── analyzer.py      # Groq API client — prompt engineering, LLM call, JSON parsing
├── models.py        # Pydantic data contracts — shared schema for all modules
├── requirements.txt # Pinned Python dependencies
├── .env.example     # Environment variable template (committed — no real keys)
├── .gitignore       # Ignores .env, __pycache__, venv, uploads, etc.
└── README.md        # This file
```

> **Integration note for the repo integrator:** Drop this folder as-is into the monorepo root alongside the other four module folders. No path changes needed — all paths inside the code are relative.

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | 0.115.6 | REST API framework |
| `uvicorn[standard]` | 0.32.1 | ASGI server |
| `python-multipart` | 0.0.20 | File upload support |
| `pdfplumber` | 0.11.4 | PDF text extraction |
| `python-docx` | 1.1.2 | DOCX text extraction |
| `groq` | ≥1.5.0 | Groq API client |
| `pydantic` | 2.10.3 | Data validation |
| `python-dotenv` | 1.0.1 | `.env` file loading |

---

## CORS

CORS is enabled for all origins (`*`) so any frontend or other module can call this API during development. Tighten this in production by setting `allow_origins` to specific domains in `main.py`.
