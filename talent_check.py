import json

def calculate_talent_check(company_name, candidate_profile, company_benchmarks):
    # 1. Get the required levels for the selected company
    requirements = company_benchmarks.get(company_name)
    if not requirements:
        return {"error": f"Company '{company_name}' not found."}

    # 2. Extract candidate skills and convert the 0-100 confidence to a 1-10 scale
    candidate_skills = {}
    for skill in candidate_profile.get("skills", []):
        cat_code = skill.get("category_code")
        confidence = skill.get("confidence")
        
        # Convert confidence to 1-10 scale
        if confidence is not None:
            level = float(confidence) / 10.0
        else:
            level = 0.0
        
        # If multiple skills map to the same category, keep the highest score
        if cat_code:
            if cat_code not in candidate_skills or level > candidate_skills[cat_code]:
                candidate_skills[cat_code] = level

    total_score = 0.0
    skillset_gap = []
    number_of_skills = len(requirements)

    # 3. Calculate Capped Ratio & Gap Analysis
    for req_category, req_level in requirements.items():
        # If a category is missing entirely, assume the score is 0.0
        cand_level = candidate_skills.get(req_category, 0.0)
        
        # Gap is true if the candidate's level is strictly less than the required level
        has_gap = bool(cand_level < req_level)
        
        skillset_gap.append({
            "category_code": req_category,
            "required_level": req_level,
            "candidate_level": cand_level,
            "gap": has_gap
        })

        # Calculate capped ratio for the total score
        ratio = cand_level / req_level if req_level > 0 else 1.0
        capped_ratio = min(1.0, ratio)
        total_score += capped_ratio

    # 4. Final Percentage Score: average the ratios, multiply by 100, round to nearest integer
    if number_of_skills > 0:
        readiness_score = int(round((total_score / number_of_skills) * 100))
    else:
        readiness_score = 0

    # 5. Return the exact JSON required by the Data Contract
    return {
        "company": company_name,
        "skillset_gap": skillset_gap,
        "readiness_score": readiness_score
    }

# --- TESTING THE INTEGRATION ---
if __name__ == "__main__":
    # Mocking the company baseline data
    mock_company_benchmarks = {
        "Google": {
            "DSA": 8, "COD": 8, "OOD": 7, "APTI": 9, "COMM": 7, "AI": 6, 
            "CLOUD": 7, "SQL": 8, "SWE": 8, "SYSD": 8, "NETW": 5, "OS": 6
        }
    }

    # Using Priya Nair's dummy data
    priya_profile = {
        "name": "Priya Nair",
        "skills": [
            {"skill_name": "Python", "category_code": "COD", "confidence": 85},
            {"skill_name": "SQL", "category_code": "SQL", "confidence": 85},
            {"skill_name": "Machine Learning", "category_code": "AI", "confidence": 85},
            {"skill_name": "Cloud", "category_code": "CLOUD", "confidence": 25}
        ]
    }

    # Run the check!
    result = calculate_talent_check("Google", priya_profile, mock_company_benchmarks)
    print(json.dumps(result, indent=2))