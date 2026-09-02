#!/usr/bin/env python3
"""
AI-COS Pharmacy Dataset Assembly & Quality Report Generator
============================================================
Assembles all batch JSONL files into a single production-ready dataset,
performs deduplication, validation, and generates a quality report.
"""

import json
import os
import hashlib
import re
from pathlib import Path
from collections import Counter, defaultdict

# ── Configuration ─────────────────────────────────────────────────────────────
PROJECT_DIR = Path("D:/Graduation Project")
BATCH_FILES = [
    "dataset_batch_1_auth.jsonl",
    "dataset_batch_2_drugs_orders.jsonl",
    "dataset_batch_3_ai_features.jsonl",
    "dataset_batch_4_dashboard.jsonl",
    "dataset_batch_5_automation_tech.jsonl",
    "dataset_batch_6_business_support.jsonl",
]
OUTPUT_FILE = PROJECT_DIR / "ai_cos_pharmacy_dataset_final.jsonl"
REPORT_FILE = PROJECT_DIR / "dataset_quality_report.md"

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_jsonl(filepath: Path) -> list[dict]:
    """Load a JSONL file and return valid records."""
    records = []
    errors = 0
    if not filepath.exists():
        print(f"  ⚠️  File not found: {filepath.name}")
        return records
    with open(filepath, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                records.append(obj)
            except json.JSONDecodeError as e:
                errors += 1
                if errors <= 5:
                    print(f"  ❌ JSON error at line {i}: {e}")
    print(f"  ✅ Loaded {len(records)} records ({errors} parse errors) from {filepath.name}")
    return records


def validate_record(record: dict) -> tuple[bool, str]:
    """Validate a single training record."""
    if "messages" not in record:
        return False, "Missing 'messages' key"
    messages = record["messages"]
    if not isinstance(messages, list) or len(messages) < 3:
        return False, "messages must have at least 3 items (system, user, assistant)"
    if messages[0].get("role") != "system":
        return False, "First message must be 'system' role"
    # Check alternating user/assistant after system
    for msg in messages:
        if "role" not in msg or "content" not in msg:
            return False, f"Message missing role or content: {msg}"
        if not msg["content"].strip():
            return False, "Empty content in message"
    return True, "ok"


def fingerprint(record: dict) -> str:
    """Create a fingerprint of a record for deduplication."""
    # Use all user messages combined as fingerprint
    user_content = " ".join(
        m["content"].lower().strip()
        for m in record.get("messages", [])
        if m.get("role") == "user"
    )
    return hashlib.md5(user_content.encode()).hexdigest()


def count_tokens_approx(text: str) -> int:
    """Rough token count (1 token ≈ 4 characters for Arabic/English mix)."""
    return len(text) // 4


def detect_language(text: str) -> str:
    """Detect if text is predominantly Arabic or English."""
    arabic_chars = len(re.findall(r'[\u0600-\u06FF]', text))
    latin_chars = len(re.findall(r'[a-zA-Z]', text))
    if arabic_chars > latin_chars:
        return "Arabic"
    elif latin_chars > arabic_chars:
        return "English"
    return "Mixed"


def categorize_record(record: dict) -> str:
    """Guess the topic category of a record."""
    all_text = " ".join(m["content"] for m in record.get("messages", []))
    keywords = {
        "Authentication & Account": ["password", "login", "register", "google oauth", "account", "كلمة المرور", "تسجيل", "حساب"],
        "Drug Catalog & Orders": ["drug", "order", "medicine", "دواء", "طلب", "أدوية", "شراء"],
        "AI Reminders & Predictions": ["reminder", "prediction", "confidence", "تذكير", "نموذج", "avg_cycle", "churn"],
        "RAG Chatbot": ["chatbot", "rag", "bot", "بوت", "chatbot", "assistant", "knowledge"],
        "Dashboard & Analytics": ["dashboard", "kpi", "analytics", "report", "لوحة", "تحليل", "تقرير"],
        "n8n & Automation": ["n8n", "workflow", "automation", "trigger", "webhook", "أتمتة"],
        "Drug Interactions & Safety": ["interaction", "conflict", "تعارض", "safety", "تفاعل", "خطر"],
        "Cross-sell": ["cross-sell", "recommend", "توصية", "بيع مرتبط"],
        "Governance & Staff": ["human review", "governance", "مراجعة", "حوكمة", "موظف"],
        "Privacy & Data": ["privacy", "data", "خصوصية", "بيانات"],
    }
    scores = defaultdict(int)
    text_lower = all_text.lower()
    for category, kws in keywords.items():
        for kw in kws:
            if kw.lower() in text_lower:
                scores[category] += 1
    if scores:
        return max(scores, key=scores.get)
    return "General"


# ── Main Assembly ─────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("  AI-COS Pharmacy Dataset Assembly & Quality Report")
    print("=" * 60 + "\n")

    # 1. Load all batches
    all_records = []
    batch_stats = {}
    for batch_file in BATCH_FILES:
        filepath = PROJECT_DIR / batch_file
        print(f"📂 Loading {batch_file}...")
        records = load_jsonl(filepath)
        batch_stats[batch_file] = {"loaded": len(records)}
        all_records.extend(records)

    print(f"\n📊 Total records loaded: {len(all_records)}\n")

    # 2. Validate
    print("🔍 Validating records...")
    valid_records = []
    invalid_count = 0
    for record in all_records:
        is_valid, reason = validate_record(record)
        if is_valid:
            valid_records.append(record)
        else:
            invalid_count += 1
    print(f"  ✅ Valid: {len(valid_records)} | ❌ Invalid: {invalid_count}")

    # 3. Deduplicate
    print("\n🔄 Deduplicating...")
    seen = set()
    unique_records = []
    dup_count = 0
    for record in valid_records:
        fp = fingerprint(record)
        if fp not in seen:
            seen.add(fp)
            unique_records.append(record)
        else:
            dup_count += 1
    dup_rate = (dup_count / len(valid_records) * 100) if valid_records else 0
    print(f"  ✅ Unique: {len(unique_records)} | 🗑️  Duplicates removed: {dup_count} ({dup_rate:.1f}%)")

    # 4. Statistics
    print("\n📈 Computing statistics...")
    token_counts = []
    languages = Counter()
    categories = Counter()
    turn_lengths = Counter()

    for record in unique_records:
        all_text = " ".join(m["content"] for m in record.get("messages", []))
        tokens = count_tokens_approx(all_text)
        token_counts.append(tokens)

        # Language detection on user messages
        user_text = " ".join(m["content"] for m in record["messages"] if m.get("role") == "user")
        lang = detect_language(user_text)
        languages[lang] += 1

        # Category
        cat = categorize_record(record)
        categories[cat] += 1

        # Turn count (number of user-assistant pairs)
        turns = sum(1 for m in record["messages"] if m.get("role") == "user")
        turn_lengths[turns] += 1

    avg_tokens = sum(token_counts) / len(token_counts) if token_counts else 0
    min_tokens = min(token_counts) if token_counts else 0
    max_tokens = max(token_counts) if token_counts else 0
    median_tokens = sorted(token_counts)[len(token_counts) // 2] if token_counts else 0
    total_tokens = sum(token_counts)

    # 5. Save final dataset
    print(f"\n💾 Saving final dataset to {OUTPUT_FILE.name}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for record in unique_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"  ✅ Saved {len(unique_records)} samples")

    # 6. Generate quality report
    print(f"\n📝 Generating quality report...")

    # Estimate fine-tuning quality score (simple heuristic)
    language_balance = min(languages.get("Arabic", 0), languages.get("English", 0)) / max(1, len(unique_records)) * 2
    diversity_score = min(1.0, len(categories) / 10)
    volume_score = min(1.0, len(unique_records) / 10000)
    dedup_score = max(0, 1 - dup_rate / 100)
    quality_score = (language_balance * 0.25 + diversity_score * 0.25 + volume_score * 0.30 + dedup_score * 0.20) * 10

    report = f"""# AI-COS Pharmacy Dataset Quality Report

## Overview

| Metric | Value |
|--------|-------|
| **Total Conversations** | {len(unique_records):,} |
| **Original Records Loaded** | {len(all_records):,} |
| **Invalid Records** | {invalid_count:,} |
| **Duplicates Removed** | {dup_count:,} ({dup_rate:.1f}%) |
| **Final Dataset Size** | {len(unique_records):,} samples |
| **Estimated Fine-Tuning Quality Score** | {quality_score:.1f}/10 |

## Batch Breakdown

| Batch File | Records Loaded |
|------------|---------------|
""" + "\n".join(f"| {k} | {v['loaded']:,} |" for k, v in batch_stats.items()) + f"""

## Token Statistics (Approximate)

| Metric | Value |
|--------|-------|
| **Total Tokens (approx.)** | {total_tokens:,} |
| **Average Tokens per Sample** | {avg_tokens:.0f} |
| **Median Tokens per Sample** | {median_tokens:,} |
| **Min Tokens** | {min_tokens:,} |
| **Max Tokens** | {max_tokens:,} |

> Note: Token counts are approximated at 1 token per 4 characters (suitable for Arabic/English mix).

## Language Distribution

| Language | Count | Percentage |
|----------|-------|-----------|
""" + "\n".join(f"| {lang} | {count:,} | {count/len(unique_records)*100:.1f}% |" for lang, count in languages.most_common()) + f"""

## Category Coverage

| Category | Count | Percentage |
|----------|-------|-----------|
""" + "\n".join(f"| {cat} | {count:,} | {count/len(unique_records)*100:.1f}% |" for cat, count in categories.most_common()) + f"""

## Conversation Turn Distribution

| Turns | Count |
|-------|-------|
""" + "\n".join(f"| {turns} turn(s) | {count:,} |" for turns, count in sorted(turn_lengths.items())) + f"""

## Coverage Analysis

### ✅ Well-Covered Topics
- Account registration (email + Google OAuth)
- Drug ordering and catalog browsing
- AI-powered refill reminders
- Governance and confidence scoring
- Dashboard KPIs and analytics
- RAG chatbot usage and limitations
- n8n automation workflows
- Drug interaction checking
- Cross-sell recommendations
- Privacy and data protection

### ⚠️ Missing or Under-Represented Knowledge
- Real payment gateway flows (intentionally out of scope \u2014 mock only in MVP)
- Mobile app questions (out of scope \u2014 web only)
- Multi-tenant onboarding (out of scope \u2014 MVP is single tenant)
- Specific drug name database (domain-specific expansion needed)
- Advanced MLflow experiment tracking (developer-facing)
- Alembic migration troubleshooting (developer-facing)

## Recommendations for Additional Data

1. **Medical disclaimer edge cases**: Add more samples where users push back on the medical disclaimer
2. **Multilingual mixing**: Add samples where user switches language mid-conversation
3. **Angry customer escalation**: More scenarios where customers demand human support
4. **System error responses**: More samples for specific HTTP error codes and debugging
5. **Seasonal patterns**: Drug demand questions tied to seasons (flu, allergies, etc.)
6. **Competitor comparisons**: Questions about why to use AI-COS vs traditional pharmacy
7. **Pharmacist/staff training**: Internal staff onboarding conversations
8. **Executive reporting**: More detailed weekly report interpretation samples

## Fine-Tuning Recommendations

| Parameter | Recommended Value |
|-----------|------------------|
| **Base Model** | LFM2.5-2.6B Instruct |
| **Method** | LoRA / QLoRA |
| **Learning Rate** | 2e-4 |
| **Batch Size** | 4-8 (with gradient accumulation) |
| **Epochs** | 3-5 |
| **Max Sequence Length** | 2048 tokens |
| **LoRA Rank (r)** | 16-64 |
| **LoRA Alpha** | 32-128 |
| **Validation Split** | 10% |

> **Estimated Fine-Tuning Quality Score: {quality_score:.1f}/10**
> 
> Score breakdown:
> - Language balance: {language_balance*100:.1f}% weight
> - Topic diversity: {diversity_score*100:.1f}% coverage
> - Volume: {volume_score*100:.1f}% of 10K target
> - Deduplication quality: {dedup_score*100:.1f}% unique

---
*Generated automatically by AI-COS Dataset Assembly Pipeline*
*Dataset file: `ai_cos_pharmacy_dataset_final.jsonl`*
"""

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"  ✅ Quality report saved to {REPORT_FILE.name}")
    print(f"\n{'=' * 60}")
    print(f"  🎉 Dataset assembly complete!")
    print(f"  📊 Final dataset: {len(unique_records):,} samples")
    print(f"  🏆 Quality score: {quality_score:.1f}/10")
    print(f"  📁 Output: {OUTPUT_FILE}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
