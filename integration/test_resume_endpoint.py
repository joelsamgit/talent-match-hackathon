"""Quick test for /flow/resume endpoint."""
import requests
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
resume_path = REPO_ROOT / "resume_pars" / "tests" / "sample_resume.docx"

print(f"Uploading: {resume_path}")
print(f"Exists: {resume_path.exists()}")

try:
    with open(resume_path, "rb") as f:
        resp = requests.post(
            "http://127.0.0.1:8000/flow/resume",
            files={"file": ("sample_resume.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
    print(f"Status: {resp.status_code}")
    if resp.status_code != 200:
        print(f"Error detail: {resp.text[:3000]}")
    else:
        import json
        data = resp.json()
        print(f"Fields: {json.dumps(data.get('fields', {}), indent=2)}")
        print(f"Skills count: {len(data.get('skills', []))}")
except Exception as e:
    print(f"Error: {e}")
