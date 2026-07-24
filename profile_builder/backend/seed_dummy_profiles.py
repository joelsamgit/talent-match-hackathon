"""
Run this first. Writes 2-3 dummy profiles to disk in the shared contract shape
so Talent Check and Skill Matching can start building/testing against real files
before your form is done. Deliberately different skill sets so downstream
scoring visibly differs per candidate (a "done" requirement in the brief).
"""
import json
import os
from schema import empty_profile, make_skill

PROFILES_DIR = os.path.join(os.path.dirname(__file__), "profiles")
os.makedirs(PROFILES_DIR, exist_ok=True)


def save_profile(profile: dict, profile_id: str):
    path = os.path.join(PROFILES_DIR, f"{profile_id}.json")
    with open(path, "w") as f:
        json.dump(profile, f, indent=2)
    return path


def load_profile(profile_id: str):
    path = os.path.join(PROFILES_DIR, f"{profile_id}.json")
    with open(path, "r") as f:
        return json.load(f)


if __name__ == "__main__":
    # Systems-leaning generalist
    p1 = empty_profile()
    p1.update({
        "name": "Arjun Mehta",
        "email": "arjun.mehta@example.com",
        "education": "B.Tech Computer Science",
        "skills": [
            make_skill("Java", "COD", "3 backend projects using Java/Spring", 85),
            make_skill("System Design", "SYSD", "Designed a URL shortener at scale", 85),
            make_skill("Networking", "NETW", "Coursework + CCNA basics", 55),
            make_skill("SQL", "SQL", "Used PostgreSQL in capstone", 55),
        ],
        "hackathons": ["Smart India Hackathon 2024"],
        "internships": ["Backend intern, fintech startup"],
        "certifications": [],
        "preferred_roles": ["Software Engineer"],
        "cv_file": "arjun_mehta_resume.pdf"
    })
    save_profile(p1, "candidate_1")

    # Data-leaning analyst
    p2 = empty_profile()
    p2.update({
        "name": "Priya Nair",
        "email": "priya.nair@example.com",
        "education": "B.Sc Statistics",
        "skills": [
            make_skill("Python", "COD", "Used in all coursework projects", 85),
            make_skill("SQL", "SQL", "Built dashboards on PostgreSQL", 85),
            make_skill("Machine Learning", "AI", "Kaggle competitions, 2 projects", 85),
            make_skill("Cloud", "CLOUD", "AWS S3/EC2 basics", 25),
        ],
        "hackathons": [],
        "internships": ["Data analyst intern, retail analytics"],
        "certifications": ["Google Data Analytics Certificate"],
        "preferred_roles": ["Data Scientist", "Data Analyst"],
        "cv_file": "priya_nair_resume.pdf"
    })
    save_profile(p2, "candidate_2")

    # Entry-level support-oriented
    p3 = empty_profile()
    p3.update({
        "name": "Kevin Thomas",
        "email": "kevin.thomas@example.com",
        "education": "B.E Information Technology",
        "skills": [
            make_skill("OS", "OS", "Coursework on Linux administration", 55),
            make_skill("SQL", "SQL", "Basic queries in DBMS course", 25),
            make_skill("Communication", "COMM", "Led college tech fest team", 55),
        ],
        "hackathons": [],
        "internships": [],
        "certifications": ["ITIL Foundation"],
        "preferred_roles": ["Application Support Analyst"],
        "cv_file": "kevin_thomas_resume.pdf"
    })
    save_profile(p3, "candidate_3")

    print(f"Seeded 3 dummy profiles into {PROFILES_DIR}")
