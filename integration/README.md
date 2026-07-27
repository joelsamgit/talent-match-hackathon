# RADIX Talent Match — Unified Integration Guide

This directory contains the unified 5-step integration layer combining all hackathon modules (`JD Analytics`, `resume_pars`, `profile_builder`, `talent_check`, and `skill_matching`).

---

## 1. Required Environment Variables

Create `.env` files in `JD Analytics/`, `resume_pars/`, and `skill_matching/` (or set environment variables in your shell):

| Environment Variable | Description | Required By | Where to Get |
| :--- | :--- | :--- | :--- |
| `GROQ_API_KEY` | Primary Groq API key for Llama 3.3 70B | `JD Analytics`, `resume_pars`, `skill_matching` | [Groq Console](https://console.groq.com) |
| `GEMINI_API_KEY` | Optional fallback Gemini API key | `resume_pars` | [Google AI Studio](https://aistudio.google.com) |
| `PORT` | Optional port override (default 8000) | `integration/main.py` | Environment config |

---

## 2. Setup & Installation

From the repository root directory:

```bash
# 1. Install required Python dependencies
pip install -r "JD Analytics/requirements.txt"
pip install -r "resume_pars/requirements.txt"
pip install -r "skill_matching/requirements.txt"

# 2. Configure Groq API Key
cp "JD Analytics/.env.example" "JD Analytics/.env"
cp "resume_pars/.env.example" "resume_pars/.env"
cp "skill_matching/.env.example" "skill_matching/.env"
# Edit .env files and add your GROQ_API_KEY
```

---

## 3. Starting the Unified Application

### Start the Unified Backend API

```bash
cd integration
uvicorn main:app --reload --port 8000
```
Interactive API Documentation will be available at: `http://localhost:8000/docs`

### Start the Frontend Application

```bash
cd profile_builder/frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 4. Unified End-to-End Workflow (5 Steps)

1. **`POST /flow/jd`**: Upload Job Description file (`PDF`, `DOCX`, `TXT`) $\rightarrow$ Extract required skills.
2. **`POST /flow/resume`**: Upload Resume file (`PDF`, `DOCX`) $\rightarrow$ Extract candidate skills & bio.
3. **`POST /flow/profile`**: Save Candidate Profile (reusing Profile Builder CRUD engine).
4. **`POST /flow/talent-check`**: Select company (e.g. `Google`, `Microsoft`) $\rightarrow$ Calculate readiness score & skillset gap.
5. **`POST /flow/skill-match`**: Match candidate profile against Step 1 JD $\rightarrow$ Calculate match score & gaps.

---

## 5. Running End-to-End Automated Verification

To run the automated 5-step test script against sample test data:

```bash
cd integration
python test_end_to_end.py
```
