import requests
import time
import json

OLLAMA_API = "http://localhost:11434/api/generate"
MODELS = ["AI-COS-Qwen-2.5:latest", "AI-COS-LFM-Q4:latest"]

QUESTIONS = [
    {
        "id": "الصيدلة (Domain)",
        "prompt": "مريض يتناول دواء 'الوارفارين' (مسيل للدم)، ويشعر بصداع. هل تنصحه بأخذ 'الأسبرين' أم 'الباراسيتامول'؟ ولماذا؟"
    },
    {
        "id": "المنطق (Logic)",
        "prompt": "إذا كان لدي 3 تفاحات على الطاولة، وقمت أنت بأخذ تفاحتين منها. كم تفاحة أصبحت معك؟"
    },
    {
        "id": "الالتزام بالتعليمات (Instruction)",
        "prompt": "اشرح نظام AI-COS Pharmacy في 10 كلمات فقط لا غير."
    }
]

results = {}

for model in MODELS:
    results[model] = {}
    print(f"Testing {model}...")
    for q in QUESTIONS:
        payload = {
            "model": model,
            "prompt": q["prompt"],
            "stream": False,
            "options": {"temperature": 0.1}
        }
        start = time.time()
        try:
            r = requests.post(OLLAMA_API, json=payload).json()
            dur = r.get("eval_duration", 1) / 1e9
            toks = r.get("eval_count", 0)
            speed = toks / dur if dur > 0 else 0
            results[model][q["id"]] = {
                "answer": r.get("response", "").strip(),
                "speed": round(speed, 1)
            }
        except Exception as e:
            results[model][q["id"]] = {"answer": f"Error: {e}", "speed": 0}

with open("intel_test.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("Done")
