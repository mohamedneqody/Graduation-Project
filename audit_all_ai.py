import os
import re
import json
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = r"D:\Graduation Project"
EXCLUDE_DIRS = {".git", ".idea", ".pytest_cache", "venv", "__pycache__", "node_modules", ".next"}

PATTERNS = {
    "Local LLMs / Ollama": [
        r"ollama", r"llama", r"qwen", r"lfm", r"gemma", r"falcon", r"gguf", r"11434"
    ],
    "Cloud LLM APIs": [
        r"gemini", r"google[_\-.]genai", r"generativelanguage", r"openai", r"openrouter", r"anthropic", r"claude", r"groq"
    ],
    "Vision / OCR Models": [
        r"trocr", r"ocr", r"tesseract", r"easyocr", r"yolo", r"fastsam", r"vision", r"9202"
    ],
    "Embeddings & Vector DB": [
        r"embed", r"pgvector", r"sentence[_\-.]transformers", r"minilm", r"huggingface"
    ],
    "Agents & Workflows": [
        r"langgraph", r"n8n", r"crewai", r"marketing[_\-.]agent", r"executive[_\-.]copilot"
    ]
}

findings = {k: [] for k in PATTERNS}
file_summary = {}

for root, dirs, files in os.walk(ROOT_DIR):
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".")]
    
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        if ext in [".py", ".ts", ".tsx", ".js", ".json", ".env", ".bat", ".md", ".yaml", ".yml", ".txt", ".sql"]:
            path = os.path.join(root, f)
            rel_path = os.path.relpath(path, ROOT_DIR)
            
            # Skip massive data files from line-by-line regex spam
            if f in ["academic_benchmark.json", "final_benchmark.json", "model_comparison_live.json", "train.jsonl", "validation.jsonl", "pytest_out.txt"]:
                continue
                
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as file_obj:
                    lines = file_obj.readlines()
                    for line_num, line in enumerate(lines, start=1):
                        line_str = line.strip()
                        if not line_str or len(line_str) > 500:
                            continue
                        for category, regex_list in PATTERNS.items():
                            for r in regex_list:
                                if re.search(r, line_str, re.IGNORECASE):
                                    findings[category].append({
                                        "file": rel_path,
                                        "line": line_num,
                                        "match": r,
                                        "content": line_str[:200]
                                    })
                                    break
            except Exception as e:
                pass

with open("audit_ai_scan.json", "w", encoding="utf-8") as out:
    json.dump(findings, out, ensure_ascii=False, indent=2)

print(f"Audit completed. Total findings:")
for k, v in findings.items():
    print(f"  - {k}: {len(v)} occurrences across files")
