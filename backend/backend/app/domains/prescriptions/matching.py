import re
from rapidfuzz import fuzz, process
from app.models.drug import Drug

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'\s+', ' ', text).strip()
    # Unify mg/g/gm units WITHOUT changing numeric value
    # E.g., don't change 625mg to 1g. Just normalize " gm" to "g".
    text = text.replace('gm', 'g')
    return text

def calculate_final_score(name_score: float, strength_match: bool, form_match: bool, has_strength: bool, has_form: bool) -> float:
    # name_score is 0-100 from rapidfuzz
    score = name_score / 100.0
    
    # Weightings: Only apply strength penalty if OCR actually found a strength but it didn't match
    if has_strength:
        if strength_match:
            score += 0.2
        else:
            score -= 0.15 # Penalize mismatch, but less harshly
            
    if has_form:
        if form_match:
            score += 0.1
        
    return max(0.0, min(1.0, score))

def match_medication(med, all_drugs: list[Drug]):
    norm_name = normalize_text(med.raw_name)
    norm_strength = normalize_text(med.strength)
    norm_form = normalize_text(med.dosage_form)
    
    if not norm_name:
        return {"matched_drug_id": None, "final_score": 0.0, "candidates": [], "candidate_margin": None}
    
    # 1. Exact match on normalized_name + strength
    search_term = f"{norm_name} {norm_strength}".strip()
    for drug in all_drugs:
        drug_name_norm = normalize_text(drug.name)
        if drug_name_norm == search_term or drug_name_norm == norm_name:
            # We found an exact match
            return {
                "matched_drug_id": drug.drug_id,
                "final_score": 1.0,
                "candidates": [{"drug_id": str(drug.drug_id), "name": drug.name, "final_score": 1.0}],
                "candidate_margin": 1.0
            }
            
    # 2. Fuzzy match
    choices = [normalize_text(d.name) for d in all_drugs]
    results = process.extract(norm_name, choices, scorer=fuzz.WRatio, limit=5)
    
    candidates = []
    for match_text, name_score, idx in results:
        drug = all_drugs[idx]
        drug_name_norm = normalize_text(drug.name)
        
        has_strength = bool(norm_strength and norm_strength != 'null')
        has_form = bool(norm_form and norm_form != 'null')
        
        strength_match = norm_strength in drug_name_norm if has_strength else False
        form_match = norm_form in drug_name_norm if has_form else False
        
        final_score = calculate_final_score(name_score, strength_match, form_match, has_strength, has_form)
        
        candidates.append({
            "drug_id": str(drug.drug_id),
            "name": drug.name,
            "final_score": final_score
        })
        
    # Sort descending
    candidates.sort(key=lambda x: x["final_score"], reverse=True)
    
    if not candidates:
        return {"matched_drug_id": None, "final_score": 0.0, "candidates": [], "candidate_margin": None}
        
    top_candidate = candidates[0]
    candidate_margin = None
    
    if len(candidates) > 1:
        candidate_margin = top_candidate["final_score"] - candidates[1]["final_score"]
        
    return {
        "matched_drug_id": top_candidate["drug_id"],
        "final_score": top_candidate["final_score"],
        "candidates": candidates,
        "candidate_margin": candidate_margin
    }
