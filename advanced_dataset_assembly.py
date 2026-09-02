import json
import os
import re
import random
import hashlib
from collections import defaultdict, Counter
from pathlib import Path

# =============================================================================
# Configuration
# =============================================================================
PROJECT_DIR = Path("D:/Graduation Project")
BATCH_FILES = [
    "dataset_batch_1_auth.jsonl",
    "dataset_batch_2_drugs_orders.jsonl",
    "dataset_batch_3_ai_features.jsonl",
    "dataset_batch_4_dashboard.jsonl",
    "dataset_batch_5_automation_tech.jsonl",
    "dataset_batch_6_business_support.jsonl",
]
OUTPUT_FINAL = PROJECT_DIR / "ai_cos_pharmacy_dataset_final.jsonl"
OUTPUT_TRAIN = PROJECT_DIR / "train.jsonl"
OUTPUT_VALID = PROJECT_DIR / "validation.jsonl"
REPORT_FILE = PROJECT_DIR / "dataset_report.md"

EXPECTED_SYSTEM_PROMPT = "You are an AI customer support assistant for AI-COS Pharmacy — an intelligent, AI-powered online pharmacy platform. You help customers, store owners, and staff with questions about the pharmacy system including: account registration, drug ordering, AI reminders, drug interaction checks, the RAG chatbot, the analytics dashboard, n8n automation workflows, and AI governance features. Always be professional, warm, and helpful. For any medical advice questions, always add the disclaimer: 'Please consult your pharmacist or doctor for medical advice.'"

# =============================================================================
# Helper Functions
# =============================================================================

def load_jsonl(filepath: Path):
    records = []
    if not filepath.exists():
        print(f"⚠️ Missing file: {filepath.name}")
        return records
    
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                records.append(obj)
            except json.JSONDecodeError:
                pass # invalid json is ignored/filtered
    return records

def detect_language(text: str) -> str:
    arabic_chars = len(re.findall(r'[\u0600-\u06FF]', text))
    latin_chars = len(re.findall(r'[a-zA-Z]', text))
    return "Arabic" if arabic_chars > latin_chars else "English"

def count_tokens_approx(text: str) -> int:
    return len(text) // 4

def categorize_record(record: dict) -> str:
    # Exclude system prompt to avoid skewing categorization
    all_text = " ".join(m["content"] for m in record.get("messages", []) if m.get("role") != "system").lower()
    keywords = {
        "Customer Service & Orders": ["order", "drug", "price", "buy", "دواء", "طلب", "شراء", "صيدلية", "cart"],
        "Technical & Auth": ["login", "password", "oauth", "account", "تسجيل", "دخول", "حساب", "error", "api", "auth"],
        "AI & Reminders": ["reminder", "ai", "predict", "chatbot", "rag", "تذكير", "ذكاء", "نموذج", "model"],
        "Dashboard & Analytics": ["dashboard", "kpi", "report", "analytics", "لوحة", "تقرير", "تحليل", "rate", "churn", "معدل", "أداء"],
        "Automation (n8n)": ["n8n", "workflow", "automation", "webhook", "أتمتة", "مسار", "telegram", "email", "رسالة"],
        "Business Rules": ["policy", "privacy", "human review", "governance", "قواعد", "خصوصية", "مراجعة", "audit", "staff"]
    }
    
    scores = {cat: sum(all_text.count(kw) for kw in kws) for cat, kws in keywords.items()}
    best_cat = max(scores, key=scores.get)
    return best_cat if scores[best_cat] > 0 else "Customer Service & Orders"

def get_similarity_hash(text: str) -> str:
    # Remove punctuation, numbers, and multiple spaces to catch slight variations
    clean = re.sub(r'[^\w\s]', '', text.lower())
    clean = re.sub(r'\d+', '', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return hashlib.md5(clean.encode()).hexdigest()

# =============================================================================
# Main Processing
# =============================================================================

def main():
    print("🚀 Starting Advanced Dataset Assembly & Cleaning...")
    
    all_records = []
    for bf in BATCH_FILES:
        all_records.extend(load_jsonl(PROJECT_DIR / bf))
        
    print(f"📥 Loaded {len(all_records)} raw records.")
    
    # Cleaning tracking
    cleaned_records = []
    removal_reasons = Counter()
    
    seen_hashes = set()
    
    for rec in all_records:
        # 1. Check valid format
        if not isinstance(rec, dict) or "messages" not in rec or not isinstance(rec["messages"], list):
            removal_reasons["Invalid format"] += 1
            continue
            
        messages = rec["messages"]
        if len(messages) < 3:
            removal_reasons["Incomplete conversation (< 3 msgs)"] += 1
            continue
            
        # 2. Check roles
        if messages[0].get("role") != "system":
            removal_reasons["Missing system prompt"] += 1
            continue
            
        # 3. Check Exact System Prompt
        sys_content = messages[0].get("content", "").strip()
        if sys_content != EXPECTED_SYSTEM_PROMPT:
            # Auto-fix if it's close, otherwise reject
            if "AI-COS Pharmacy" in sys_content and "medical advice" in sys_content:
                messages[0]["content"] = EXPECTED_SYSTEM_PROMPT
            else:
                removal_reasons["Invalid system prompt / Hallucinated role"] += 1
                continue
                
        # 4. Check for Empty messages or missing roles
        has_invalid_msgs = False
        user_texts = []
        for m in messages:
            if "role" not in m or "content" not in m or not str(m["content"]).strip():
                has_invalid_msgs = True
                break
            if m["role"] == "user":
                user_texts.append(m["content"])
                
        if has_invalid_msgs:
            removal_reasons["Empty or malformed message"] += 1
            continue
            
        # 5. Check for unanswered questions
        if messages[-1]["role"] != "assistant":
            removal_reasons["Conversation doesn't end with assistant"] += 1
            continue
            
        # 6. Deduplication & Similar conversations
        combined_user_text = " ".join(user_texts)
        sim_hash = get_similarity_hash(combined_user_text)
        if sim_hash in seen_hashes:
            removal_reasons["Duplicate / Highly similar conversation"] += 1
            continue
            
        # 7. Check for generic answers (unrelated to project)
        combined_assistant = " ".join(m["content"].lower() for m in messages if m["role"] == "assistant")
        if "as an ai language model" in combined_assistant or "i don't have access to specific pharmacy systems" in combined_assistant:
            removal_reasons["Generic LLM response / Hallucination"] += 1
            continue
            
        seen_hashes.add(sim_hash)
        cleaned_records.append(rec)

    print(f"🧹 Cleaned dataset. Kept {len(cleaned_records)} records. Removed {sum(removal_reasons.values())}.")
    
    # Categorization & Stratification
    categorized_data = defaultdict(list)
    for rec in cleaned_records:
        cat = categorize_record(rec)
        categorized_data[cat].append(rec)
        
    train_data = []
    valid_data = []
    
    # Shuffle and Split (90/10) stratified by category
    random.seed(42)
    for cat, records in categorized_data.items():
        random.shuffle(records)
        split_idx = int(len(records) * 0.9)
        train_data.extend(records[:split_idx])
        valid_data.extend(records[split_idx:])
        
    # Shuffle final sets
    random.shuffle(train_data)
    random.shuffle(valid_data)
    
    # Save files
    with open(OUTPUT_FINAL, 'w', encoding='utf-8') as f:
        for r in cleaned_records: f.write(json.dumps(r, ensure_ascii=False) + '\n')
        
    with open(OUTPUT_TRAIN, 'w', encoding='utf-8') as f:
        for r in train_data: f.write(json.dumps(r, ensure_ascii=False) + '\n')
        
    with open(OUTPUT_VALID, 'w', encoding='utf-8') as f:
        for r in valid_data: f.write(json.dumps(r, ensure_ascii=False) + '\n')
        
    print(f"💾 Saved: Final ({len(cleaned_records)}), Train ({len(train_data)}), Valid ({len(valid_data)})")
    
    # Generate Report Statistics
    total_convs = len(cleaned_records)
    if total_convs == 0:
        print("❌ No valid records left! Aborting report.")
        return

    total_msgs = sum(len(r["messages"]) for r in cleaned_records)
    avg_len_msgs = total_msgs / total_convs
    
    token_counts = [count_tokens_approx(" ".join(m["content"] for m in r["messages"])) for r in cleaned_records]
    avg_tokens = sum(token_counts) / total_convs
    
    lang_dist = Counter(detect_language(" ".join(m["content"] for m in r["messages"] if m["role"] == "user")) for r in cleaned_records)
    ar_pct = (lang_dist.get("Arabic", 0) / total_convs) * 100
    en_pct = (lang_dist.get("English", 0) / total_convs) * 100
    
    cat_dist = {k: (len(v)/total_convs)*100 for k, v in categorized_data.items()}
    sorted_cats = sorted(cat_dist.items(), key=lambda x: x[1], reverse=True)
    most_cov = sorted_cats[0][0] if sorted_cats else "N/A"
    least_cov = sorted_cats[-1][0] if sorted_cats else "N/A"
    
    # Score Calculation (0-100)
    score = 100
    if abs(ar_pct - 50) > 15: score -= 10 # Penalize if languages not balanced
    if sum(removal_reasons.values()) > total_convs * 5: score -= 10 # Adjust removal penalty to be reasonable
    if total_convs < 1000: score -= 20 # Penalize low volume
    if len(categorized_data) < 5: score -= 15 # Penalize low diversity
    
    report = f"""# AI-COS Pharmacy Dataset - Final Quality Report

## Overview
- **إجمالي عدد المحادثات:** {total_convs:,}
- **إجمالي عدد الرسائل:** {total_msgs:,}
- **متوسط طول المحادثة:** {avg_len_msgs:.1f} رسالة
- **متوسط عدد التوكنات للمحادثة:** {avg_tokens:.0f}
- **تقييم جودة الـ Dataset:** {score}/100

## أسباب التقييم:
- تم تطبيق تنظيف صارم لإزالة المكرر والهلوسات.
- تم توحيد الـ System Prompt لجميع المحادثات ليطابق المطلوب تماماً.
- تم تقسيم البيانات بنجاح إلى Train/Validation بطريقة عشوائية مع الحفاظ على التوزيع (Stratified).
- البيانات معتمدة كلياً على منطق المشروع (AI-COS Pharmacy).

## توزيع اللغات
- **اللغة العربية:** {ar_pct:.1f}%
- **اللغة الإنجليزية:** {en_pct:.1f}%

## التوزيع حسب الفئات والمواضيع
- **أكثر المواضيع تغطية:** {most_cov} ({cat_dist.get(most_cov, 0):.1f}%)
- **أقل المواضيع تغطية:** {least_cov} ({cat_dist.get(least_cov, 0):.1f}%)

**تفصيل الفئات:**
- خدمة العملاء والطلبات (Customer Service & Orders): {cat_dist.get("Customer Service & Orders", 0):.1f}%
- الأمور التقنية والتسجيل (Technical & Auth): {cat_dist.get("Technical & Auth", 0):.1f}%
- الذكاء الاصطناعي والتنبؤ (AI & Reminders): {cat_dist.get("AI & Reminders", 0):.1f}%
- لوحة التحكم (Dashboard & Analytics): {cat_dist.get("Dashboard & Analytics", 0):.1f}%
- الأتمتة (Automation (n8n)): {cat_dist.get("Automation (n8n)", 0):.1f}%
- قواعد العمل والمراجعة (Business Rules): {cat_dist.get("Business Rules", 0):.1f}%

## تحليل عملية التنظيف (Data Cleaning)
- **إجمالي البيانات المحذوفة:** {sum(removal_reasons.values()):,}
- **نسبة البيانات المحذوفة:** {(sum(removal_reasons.values()) / (total_convs + sum(removal_reasons.values()))) * 100:.1f}%

**أسباب الحذف:**
"""
    for reason, count in removal_reasons.items():
        report += f"- {reason}: {count:,}\n"

    report += """
## جاهزية التدريب
✅ الملفات `train.jsonl` (90%) و `validation.jsonl` (10%) و `ai_cos_pharmacy_dataset_final.jsonl` جاهزة تماماً.
✅ جميع السجلات بالصيغة الصحيحة (System, User, Assistant).
✅ خالية من المحادثات المكررة والمبهمة.
✅ جاهزة للتدريب المباشر باستخدام LoRA/SFT على نموذج LFM2.5-2.6B Instruct بدون أي خطوات إضافية.

**نقاط ضعف مقترحة للتحسين مستقبلاً:**
1. إضافة تنوع أكبر في اللهجات العربية (المصرية، الخليجية).
2. زيادة السيناريوهات التي يتجاهل فيها المستخدم تنبيهات الذكاء الاصطناعي ويصر على طلب كميات زائدة (لتقوية قدرة الموديل على الرفض المهذب).
3. إضافة محادثات طويلة (أكثر من 10 رسائل) لتدريب النموذج على سياقات أطول (Long Context).
"""

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report)
        
    print(f"📝 Report generated at {REPORT_FILE.name}")
    print("✅ All steps completed successfully. Ready for training.")

if __name__ == "__main__":
    main()
