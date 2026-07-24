import json

def calculate_talent_check(company_name, candidate_profile, company_benchmarks):
    # 1. Get the required levels for the selected company
    requirements = company_benchmarks.get(company_name)
    if not requirements:
        return {"error": f"Company '{company_name}' not found in benchmark data."}

    # 2. Extract candidate skills and convert the 0-100 confidence to a 1-10 scale
    candidate_skills = {}
    for skill in candidate_profile.get("skills", []):
        cat_code = skill.get("category_code")
        confidence = skill.get("confidence")
        
        # Convert 0-100 scale to 1-10 scale (e.g., 85 -> 8.5)
        level = (confidence / 10.0) if confidence else 0.0
        
        # Keep the highest score if multiple skills map to the same category
        if cat_code not in candidate_skills or level > candidate_skills[cat_code]:
            candidate_skills[cat_code] = level

    total_score = 0
    skillset_gap = []
    number_of_skills = len(requirements)

    # 3. Calculate Capped Ratio & Gap Analysis
    for req_category, req_level in requirements.items():
        cand_level = candidate_skills.get(req_category, 0.0)
        
        # Gap is true if candidate's level is less than the required level
        has_gap = bool(cand_level < req_level)
        
        skillset_gap.append({
            "category_code": req_category,
            "required_level": req_level,
            "candidate_level": float(cand_level),
            "gap": has_gap
        })

        # Calculate capped ratio for the total score
        ratio = cand_level / req_level if req_level > 0 else 1.0
        capped_ratio = min(1.0, ratio)
        total_score += capped_ratio

    # 4. Final Percentage Score
    readiness_score = round((total_score / number_of_skills) * 100)

    # 5. Return the exact JSON required by the Data Contract
    return {
        "company": company_name,
        "skillset_gap": skillset_gap,
        "readiness_score": readiness_score
    }

# --- TESTING THE INTEGRATION LCOALLY ---
if __name__ == "__main__":
    with open('talent_check_company_skillsets.json', 'r') as f:
        mock_benchmarks = json.load(f)

    mock_profile = {
        "name": "Priya Nair",
        "skills": [
            {"skill_name": "Python", "category_code": "COD", "confidence": 85},
            {"skill_name": "SQL", "category_code": "SQL", "confidence": 85},
            {"skill_name": "Machine Learning", "category_code": "AI", "confidence": 85},
            {"skill_name": "Cloud", "category_code": "CLOUD", "confidence": 25}
        ]
    }

    result = calculate_talent_check("Google", mock_profile, mock_benchmarks)
    print(json.dumps(result, indent=2))