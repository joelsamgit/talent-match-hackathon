"""Quick test for /flow/jd endpoint."""
import requests
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
jd_path = REPO_ROOT / "JD Analytics" / "tests" / "fixtures" / "sample_jd.txt"

print(f"Uploading: {jd_path}")
print(f"Exists: {jd_path.exists()}")

try:
    with open(jd_path, "rb") as f:
        resp = requests.post(
            "http://127.0.0.1:8000/flow/jd",
            files={"file": ("sample_jd.txt", f, "text/plain")},
        )
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:2000]}")
except Exception as e:
    print(f"Error: {e}")
