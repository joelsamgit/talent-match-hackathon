# Role 4: Talent Check

This module compares a candidate's profile against a company's baseline expectations across 12 RADIX skillsets.

## How to Run

1. Navigate to this folder (`cd talent_check`).
2. Install dependencies: `pip install -r requirements.txt`
3. Start the API server on port 8002: `uvicorn main:app --reload --port 8002`

## API Contract

**POST `/talent-check`**

**Input Payload:**
```json
{
  "company_name": "Google",
  "candidate_profile": {
    "name": "Arjun",
    "skills": [
      { "category_code": "COD", "confidence": 85 }
    ]
  }
}