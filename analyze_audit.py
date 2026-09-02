import json
import os
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open("audit_ai_scan.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Group findings by unique files and key components
components = {
    "1. Chatbot & RAG Service (Local LLM & Cloud Fallback)": set(),
    "2. AI Agents & Model Manager (Switching, Modelfiles)": set(),
    "3. Prescription Vision & OCR Server (TrOCR, Gemini Vision, Image Processing)": set(),
    "4. Predictive AI & ML Models (Purchase Cycle, Churn, XGBoost, SHAP)": set(),
    "5. Embeddings & Semantic Search (pgvector, MiniLM)": set(),
    "6. Automation & External AI Workflows (n8n, Webhooks)": set(),
    "7. Launch Scripts & Environment Config (.env, .bat)": set()
}

for cat, items in data.items():
    for item in items:
        fpath = item["file"].replace("\\", "/")
        # Categorize
        if "domains/ai/" in fpath or "domains/chat/" in fpath or "service.py" in fpath:
            components["1. Chatbot & RAG Service (Local LLM & Cloud Fallback)"].add(fpath)
        elif "domains/agents/" in fpath or "model_manager" in fpath:
            components["2. AI Agents & Model Manager (Switching, Modelfiles)"].add(fpath)
        elif "upload/" in fpath or "ocr" in fpath.lower() or "trocr" in fpath.lower() or "vision" in fpath.lower():
            components["3. Prescription Vision & OCR Server (TrOCR, Gemini Vision, Image Processing)"].add(fpath)
        elif "prediction" in fpath.lower() or "churn" in fpath.lower() or "cycle" in fpath.lower() or "ml" in fpath.lower():
            components["4. Predictive AI & ML Models (Purchase Cycle, Churn, XGBoost, SHAP)"].add(fpath)
        elif "vector" in fpath.lower() or "embed" in fpath.lower():
            components["5. Embeddings & Semantic Search (pgvector, MiniLM)"].add(fpath)
        elif "n8n" in fpath.lower() or "workflow" in fpath.lower():
            components["6. Automation & External AI Workflows (n8n, Webhooks)"].add(fpath)
        elif fpath.endswith(".env") or fpath.endswith(".bat") or "config" in fpath:
            components["7. Launch Scripts & Environment Config (.env, .bat)"].add(fpath)

print("COMPONENTS INVENTORY:")
for comp, files in components.items():
    print(f"\n{comp} ({len(files)} files):")
    for f in sorted(list(files))[:15]:
        print(f"   - {f}")
