import re
from rapidfuzz import fuzz, process
from app.models.drug import Drug

# ذيول صيغ الجرعات التي يخرجها النموذج من قوالب تدريبه (مثل "- 1 cap TID") —
# تنظيفها قبل المطابقة حتى لا تخفف تشابه الاسم مع الكتالوج.
_SIG_TAIL_RE = re.compile(
    r"\s*[-–-]\s*\d+\s*(?:tab|tabs|cap|caps|tablet|tablets|capsule|capsules|sachet|sachets|drop|drops|puff|puffs|pen|pens|vial|vials|amp|amps|susp|suspension|syrup|ml)(?![a-zA-Z]).*$",
    re.IGNORECASE)
_LEADING_IDX_RE = re.compile(r"^\s*\d+[\.)]\s*")


def strip_sig_tail(text):
    t = (text or "").strip()
    t = _SIG_TAIL_RE.sub("", t)
    t = _LEADING_IDX_RE.sub("", t)
    return re.sub(r"\s+", " ", t).strip()

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    
    # Insert space between numbers and letters (e.g. 80mg -> 80 mg)
    text = re.sub(r'(\d+)([a-z]+)', r'\1 \2', text)
    # Insert space between letters and numbers (e.g. mg80 -> mg 80, though rare)
    text = re.sub(r'([a-z]+)(\d+)', r'\1 \2', text)
    
    text = re.sub(r'\s+', ' ', text).strip()
    # Unify mg/g/gm units WITHOUT changing numeric value
    # E.g., don't change 625mg to 1g. Just normalize " gm" to "g".
    text = re.sub(r'\bgm\b', 'g', text)
    return text

def calculate_final_score(name_score: float, strength_match: bool, form_match: bool, has_strength: bool, has_form: bool) -> float:
    # name_score is 0-100 from rapidfuzz
    base_score = name_score / 100.0
    
    # CRITICAL LASA GUARD: If pure name similarity is mediocre (< 0.75), cap the final score.
    # An accidental strength match (e.g. 50mg, 500mg) or form match must NEVER inflate a lookalike into an auto-match!
    if base_score < 0.75:
        return min(0.50, base_score)
        
    score = base_score
    
    # Weightings:
    if has_strength:
        if strength_match:
            # If name similarity is near-perfect (>= 0.95), allow bump to 1.0;
            # If name similarity is below 0.95 (e.g. 85% like Ramatridin vs Ramatrizine),
            # DO NOT allow strength match to inflate into an auto-match (>= 0.95)!
            if base_score >= 0.95:
                score = min(1.0, score + 0.05)
            else:
                score = min(0.88, score + 0.05)
        else:
            score -= 0.25 # Severe penalty for strength mismatch (e.g. 50mg vs 50mcg, or 10mg vs 5mg)
            
    if has_form:
        if form_match:
            score = min(1.0 if base_score >= 0.95 else 0.88, score + 0.02)
        else:
            score -= 0.05
        
    return max(0.0, min(1.0, score))

def match_medication(med, all_drugs: list[Drug]):
    # Fallback if AI hallucinates and puts name in instructions
    raw = med.raw_name or ""
    if not raw and med.instructions:
        raw = med.instructions
    elif not raw and med.dosage_form:
        raw = med.dosage_form
    raw = strip_sig_tail(raw) or raw
        
    norm_raw_name = normalize_text(raw)

    # The local OCR service returns the visible line as raw_name.  Derive a
    # structured strength when the provider could not populate it, so a dose
    # embedded in the line can never bypass the hard-stop guard.
    raw_strength = med.strength
    if not raw_strength:
        inline_strengths = re.findall(
            r'(\d+(?:\.\d+)?(?:\s*/\s*\d+(?:\.\d+)?)?\s*(?:mg|g|gm|mcg|ml|iu|%|μg))\b',
            raw,
            re.IGNORECASE,
        )
        raw_strength = inline_strengths[-1] if inline_strengths else None

    norm_strength = normalize_text(raw_strength)
    norm_name = norm_raw_name
    if norm_strength:
        norm_name = normalize_text(
            re.sub(rf'(?<!\d){re.escape(norm_strength)}\b', ' ', norm_raw_name)
        )
    norm_form = normalize_text(med.dosage_form)
    
    if not norm_name or getattr(med, "is_fragment_too_short", False):
        return {
            "matched_drug_id": None,
            "final_score": 0.0,
            "candidates": [],
            "candidate_margin": None,
            "match_status": "not_found"
        }
    
    has_strength = bool(norm_strength and norm_strength != 'null')
    has_form = bool(norm_form and norm_form != 'null')

    # Extraction helper for dosage/strength from text
    STRENGTH_REGEX = r'(\d+(?:\.\d+)?(?:\/\d+(?:\.\d+)?)?\s*(?:mg|g|mcg|ml|iu|%|μg))\b'

    def extract_strength(text: str) -> str | None:
        if not text:
            return None
        m = re.findall(STRENGTH_REGEX, text, re.IGNORECASE)
        return m[-1].strip() if m else None

    def normalize_strength_token(s: str | None) -> str | None:
        if not s or s.strip().lower() in ['null', 'none', '']:
            return None
        cleaned = s.strip().lower().replace(" ", "")
        # Grams to mg conversion (e.g. 1g -> 1000mg)
        g_match = re.match(r'^(\d+(?:\.\d+)?)(?:g|gm|gram|grams)$', cleaned)
        if g_match:
            val = float(g_match.group(1)) * 1000
            mg = int(val) if val.is_integer() else val
            return f"{mg}mg"
        return cleaned

    def evaluate_strength_compatibility(prescribed_str: str | None, catalog_str: str | None, catalog_full_name: str) -> tuple[bool, bool]:
        """
        Clinical Strength Guard:
        Prevents dangerous substring entrapment (e.g. 10mg inside 110mg).
        Returns: (strength_match: bool, strength_conflict: bool)
        """
        p_norm = normalize_strength_token(prescribed_str)
        if not p_norm:
            return (False, False)
            
        c_norm = normalize_strength_token(catalog_str)
        if c_norm:
            if p_norm == c_norm:
                return (True, False)
            # OCR unit confusion: "ml" <-> "mg" بنفس الرقم خطأ قراءة شائع
            # ("Diovan 80 ml" مقابل الكتالوج "Diovan 80mg") — نفس الرقم = نفس
            # القوة فعليًا، ولا يُعد تعارضًا خطيرًا على المريض.
            p_mg = re.match(r"^(\d+(?:\.\d+)?)mg$", p_norm)
            p_ml = re.match(r"^(\d+(?:\.\d+)?)ml$", p_norm)
            c_mg = re.match(r"^(\d+(?:\.\d+)?)mg$", c_norm)
            c_ml = re.match(r"^(\d+(?:\.\d+)?)ml$", c_norm)
            if p_mg and c_ml and p_mg.group(1) == c_ml.group(1):
                return (True, False)
            if p_ml and c_mg and p_ml.group(1) == c_mg.group(1):
                return (True, False)
            return (False, True) # Strict Hard Conflict
            
        # Catalog full name regex check with negative lookbehind/lookahead to prevent 10mg matching 110mg or 100mg
        m = re.match(r'^(\d+(?:\.\d+)?)(mg|g|mcg|ml|iu|%|μg)$', p_norm)
        if m:
            num, unit = m.groups()
            exact_pattern = rf'(?<!\d){re.escape(num)}\s*{re.escape(unit)}\b'
            if re.search(exact_pattern, catalog_full_name, re.IGNORECASE):
                return (True, False)
            else:
                other = re.search(r'(?<!\d)\d+(?:\.\d+)?\s*(?:mg|g|mcg|ml|iu|%|μg)\b', catalog_full_name, re.IGNORECASE)
                if other:
                    return (False, True)
                return (False, False)
        return (False, False)

    # 1. Exact match on normalized_name + strength
    search_term = f"{norm_name} {norm_strength}".strip() if norm_strength else norm_name
    for drug in all_drugs:
        drug_name_norm = normalize_text(drug.name)
        drug_strength = extract_strength(drug_name_norm)

        # A: Full exact match on name + strength
        if drug_name_norm == search_term:
            # v4.1 safety: an exact string match on a hallucinated line is
            # still possible. Missing or low REAL OCR confidence (v4.1 sends
            # decoder-derived confidence) must fail CLOSED to review.
            if getattr(med, "ocr_confidence", 0.0) < 0.85:
                return {
                    "matched_drug_id": None,
                    "final_score": 0.70,
                    "candidates": [{
                        "drug_id": str(drug.drug_id),
                        "name": drug.name,
                        "base_price": float(drug.base_price) if drug.base_price else 0.0,
                        "category": drug.category,
                        "image_url": drug.image_url,
                        "final_score": 0.70,
                        "strength_conflict": False,
                        "match_reason": "low_ocr_confidence_exact_match"
                    }],
                    "candidate_margin": None,
                    "match_status": "needs_review"
                }
            return {
                "matched_drug_id": drug.drug_id,
                "final_score": 1.0,
                "candidates": [{
                    "drug_id": str(drug.drug_id), 
                    "name": drug.name, 
                    "base_price": float(drug.base_price) if drug.base_price else 0.0,
                    "category": drug.category,
                    "image_url": drug.image_url,
                    "final_score": 1.0,
                    "strength_conflict": False,
                    "match_reason": "exact_match"
                }],
                "candidate_margin": 1.0,
                "match_status": "matched"
            }

        # B: Exact match on drug name alone
        if drug_name_norm == norm_name:
            s_match, s_conflict = evaluate_strength_compatibility(norm_strength, drug_strength, drug_name_norm)
            if has_strength and s_conflict:
                # CRITICAL CLINICAL SAFETY: Dose Discrepancy!
                # E.g., prescribed Drug X 10mg, but catalog has Drug X 100mg or 110mg.
                # Must NEVER auto-match as 1.0 (Green). Downgrade to needs_review (Yellow)!
                return {
                    "matched_drug_id": None,
                    "final_score": 0.70,
                    "candidates": [{
                        "drug_id": str(drug.drug_id), 
                        "name": drug.name, 
                        "base_price": float(drug.base_price) if drug.base_price else 0.0,
                        "category": drug.category,
                        "image_url": drug.image_url,
                        "final_score": 0.70,
                        "strength_conflict": True,
                        "match_reason": f"strength_discrepancy: prescribed {norm_strength} vs catalog {drug_strength or 'differing'}"
                    }],
                    "candidate_margin": None,
                    "match_status": "needs_review"
                }
            elif not has_strength:
                # OCR extracted no strength. Check if the catalog has multiple
                # drugs with the same name but different strengths — if so, it
                # is impossible to safely auto-select one; route to pharmacist.
                same_name_drugs = [
                    d for d in all_drugs
                    if normalize_text(d.name).startswith(norm_name)
                    and extract_strength(normalize_text(d.name))
                ]
                if len(same_name_drugs) > 1:
                    # Multiple strengths available — cannot auto-match safely
                    return {
                        "matched_drug_id": None,
                        "final_score": 0.70,
                        "candidates": [
                            {
                                "drug_id": str(d.drug_id),
                                "name": d.name,
                                "base_price": float(d.base_price) if d.base_price else 0.0,
                                "category": d.category,
                                "image_url": d.image_url,
                                "final_score": 0.70,
                                "strength_conflict": True,
                                "match_reason": "strength_missing_multiple_options"
                            }
                            for d in same_name_drugs
                        ],
                        "candidate_margin": None,
                        "match_status": "needs_review"
                    }
                # Only one strength in catalog — safe to auto-match, but only
                # when the recognizer itself is confident (v4.1 real confidence,
                # fail-closed default).
                if getattr(med, "ocr_confidence", 0.0) < 0.85:
                    return {
                        "matched_drug_id": None,
                        "final_score": 0.70,
                        "candidates": [{"drug_id": str(drug.drug_id), "name": drug.name,
                                        "base_price": float(drug.base_price) if drug.base_price else 0.0,
                                        "category": drug.category, "image_url": drug.image_url,
                                        "final_score": 0.70, "strength_conflict": False,
                                        "match_reason": "low_ocr_confidence_exact_match"}],
                        "candidate_margin": None,
                        "match_status": "needs_review"
                    }
                return {
                    "matched_drug_id": drug.drug_id,
                    "final_score": 1.0,
                    "candidates": [{"drug_id": str(drug.drug_id), "name": drug.name,
                                    "base_price": float(drug.base_price) if drug.base_price else 0.0,
                                    "category": drug.category, "image_url": drug.image_url,
                                    "final_score": 1.0, "strength_conflict": False,
                                    "match_reason": "exact_name_match_single_strength"}],
                    "candidate_margin": 1.0,
                    "match_status": "matched"
                }
            
    # NEW LOGIC: Prevent strength numbers from hijacking the WRatio token set
    # By removing the strength token from BOTH the search term and the database choices,
    # we force fuzz.WRatio to compare the actual drug names, not just matching "50mg" to "50mg".
    clean_search_name = norm_name
    if norm_strength and norm_strength != 'null':
        clean_search_name = clean_search_name.replace(norm_strength, "").strip()
        
    import jellyfish
    
    # 2. Phonetic & Fuzzy match with composite scorer (token_set_ratio + partial_ratio)
    choices = []
    for d in all_drugs:
        d_name = normalize_text(d.name)
        if norm_strength and norm_strength != 'null':
            d_name = d_name.replace(norm_strength, "").strip()
        choices.append(d_name)
        
    def composite_scorer(s1, s2, **kwargs):
        return max(fuzz.token_set_ratio(s1, s2, **kwargs), fuzz.partial_ratio(s1, s2, **kwargs))

    results = process.extract(clean_search_name, choices, scorer=composite_scorer, limit=15)
    
    candidates = []
    search_metaphone = jellyfish.metaphone(clean_search_name) if clean_search_name else ""
    
    for match_text, fuzzy_score, idx in results:
        drug = all_drugs[idx]
        drug_name_norm = normalize_text(drug.name)
        drug_strength = extract_strength(drug_name_norm)
        
        # Phonetic boost: compare the metaphone representation using jaro_winkler
        match_metaphone = jellyfish.metaphone(match_text) if match_text else ""
        phonetic_sim = jellyfish.jaro_winkler_similarity(search_metaphone, match_metaphone) if search_metaphone and match_metaphone else 0.0
        
        # Blend the fuzzy score (0-100) and phonetic similarity (0.0-1.0 -> 0-100)
        phonetic_score = phonetic_sim * 100
        
        # Ensure fuzzy_score checks partial alignment with the full drug string as well
        fuzzy_score = max(fuzzy_score, fuzz.partial_ratio(clean_search_name, match_text))
        
        # Only apply phonetic boost if phonetic score is very high OR fuzzy score is already decent.
        if phonetic_score > 80 or fuzzy_score > 50:
            name_score = max(fuzzy_score, phonetic_score * 0.90)
        else:
            name_score = fuzzy_score
            
        # Pure name ratio check against drug name prefix to prevent substring entrapment (e.g. 'vancocin' matching inside 'vanvilda plus')
        search_first_token = clean_search_name.split()[0] if clean_search_name else ""
        target_first_token = match_text.split()[0] if match_text else ""
        pure_name_ratio = fuzz.ratio(search_first_token, target_first_token)
        pure_name_partial = fuzz.partial_ratio(search_first_token, target_first_token)
        
        if pure_name_ratio < 65:
            name_score = min(name_score, (fuzzy_score + pure_name_ratio) / 2.0)
        
        strength_match, strength_conflict = evaluate_strength_compatibility(norm_strength, drug_strength, drug_name_norm)
        form_match = norm_form in drug_name_norm if has_form else False

        final_score = calculate_final_score(name_score, strength_match, form_match, has_strength, has_form)
        if strength_conflict:
            # Critical Dose Discrepancy Hard Stop (caps at 0.70 to force Yellow / needs_review)
            final_score = min(0.70, final_score)
        
        # Strict LASA & Look-Alike Guard:
        # Tolerate prefix OCR truncation ONLY if search token is a true suffix of target (e.g. 'maryl' in 'amaryl')
        is_truncation = (
            len(search_first_token) >= 4 and 
            target_first_token.endswith(search_first_token) and 
            pure_name_partial == 100 and
            len(search_first_token) < len(target_first_token)
        )
        
        # Suffix / spelling mutations (e.g. Concort vs Concor, Lipiton vs Lipitor, Amarly vs Amaryl)
        # MUST be flagged as LASA lookalikes to prevent deadly false-green matches.
        is_lasa_lookalike = (pure_name_ratio < 95) and not is_truncation
        
        # Only keep realistic candidates with final_score >= 0.60
        if final_score >= 0.60:
            candidates.append({
                "drug_id": str(drug.drug_id),
                "name": drug.name,
                "base_price": float(drug.base_price) if drug.base_price else 0.0,
                "category": drug.category,
                "image_url": drug.image_url,
                "final_score": final_score,
                "strength_conflict": strength_conflict,
                "is_lasa_lookalike": is_lasa_lookalike,
                "match_reason": "strength_conflict" if strength_conflict else ("lasa_warning" if is_lasa_lookalike else "fuzzy_match")
            })
        
    # Sort descending
    candidates.sort(key=lambda x: x["final_score"], reverse=True)
    
    # If no candidate scored >= 0.60 or top candidate is below 0.65, mark as NOT FOUND in catalog
    if not candidates or candidates[0]["final_score"] < 0.65:
        return {
            "matched_drug_id": None,
            "final_score": 0.0,
            "candidates": [],
            "candidate_margin": None,
            "match_status": "not_found"
        }
        
    top_candidate = candidates[0]
    candidate_margin = None
    
    if len(candidates) > 1:
        candidate_margin = top_candidate["final_score"] - candidates[1]["final_score"]
        
    # HIGH-CONFIDENCE CLINICAL TRAFFIC LIGHT:
    # 🟢 Green (matched): >= 0.95 score, clear margin (>= 0.10), NO STRENGTH CONFLICT, AND NO LASA LOOKALIKE RISK
    # 🟡 Yellow (needs_review): 0.65 - 0.94 score, OR strength conflict (e.g. 5mg vs 50mg), OR tight candidate margin (LASA risk)
    # 🔴 Red (not_found): < 0.65 score or empty candidates
    is_safe_auto_match = (
        top_candidate["final_score"] >= 0.95 and 
        (candidate_margin is None or candidate_margin >= 0.10) and 
        not top_candidate.get("strength_conflict", False) and
        not top_candidate.get("is_lasa_lookalike", False) and
        # v4.1: ocr_confidence is now a REAL decoder-derived probability.
        # Default 0.0 (not 1.0) so a missing confidence can never auto-green.
        getattr(med, "ocr_confidence", 0.0) >= 0.85
    )
    match_status = "matched" if is_safe_auto_match else "needs_review"

    return {
        "matched_drug_id": top_candidate["drug_id"] if match_status == "matched" else None,
        "final_score": top_candidate["final_score"],
        "candidates": candidates[:3],  # Keep only top 3 relevant candidates
        "candidate_margin": candidate_margin,
        "match_status": match_status
    }
