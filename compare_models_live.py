import json
import time
import requests
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

OLLAMA_API = "http://localhost:11434/api"
MODELS = ["AI-COS-Qwen-2.5:latest", "AI-COS-LFM-Q4:latest"]

TEST_CASES = [
    # 1. Identity & Team
    {
        "category": "Identity & Project Info",
        "name": "Creator & University",
        "type": "generate",
        "prompt": "من صانعك ومن المطور الرئيسي وما هي كليتك وجامعتك؟"
    },
    {
        "category": "Identity & Project Info",
        "name": "Team Members",
        "type": "generate",
        "prompt": "من هم أعضاء الفريق الذين ساعدوا المطور في بناء نظام AI-COS Pharmacy؟"
    },
    {
        "category": "Identity & Project Info",
        "name": "Role of Mohamed Yasser",
        "type": "generate",
        "prompt": "ما هو دور محمد ياسر بالتحديد في مشروع AI-COS؟"
    },
    # 2. Medical Knowledge & Categories
    {
        "category": "Medical & Pharmacy Knowledge",
        "name": "Therapeutic Category (Concor)",
        "type": "generate",
        "prompt": "ما هي الفئة العلاجية لدواء Concor وما هي استخداماته الأساسية؟"
    },
    {
        "category": "Medical & Pharmacy Knowledge",
        "name": "Drug Interaction (Warfarin + Aspirin)",
        "type": "generate",
        "prompt": "مريض يتناول دواء Warfarin ويعاني من صداع شديد، هل تنصحه بأخذ Aspirin أم Paracetamol؟ اشرح السبب الطبي بدقة."
    },
    {
        "category": "Medical & Pharmacy Knowledge",
        "name": "Chronic vs Acute Drugs",
        "type": "generate",
        "prompt": "في نظام الصيدلية، ما الفرق بين الدواء المزمن (Chronic) والدواء الحاد (Acute)؟ اذكر مثالاً لكل منهما وكيف يؤثر ذلك على التذكير الذكي."
    },
    # 3. Database Grounding & Price RAG
    {
        "category": "Database Grounding & Pricing",
        "name": "Direct Price RAG",
        "type": "generate",
        "prompt": "السياق المستخرج من قاعدة البيانات:\nدواء Alerid 10mg سعره 63.00 ج.م وهو مضاد للهستامين.\nدواء Stopadol Night سعره 30.00 ج.م مسكن.\n\nسؤال المستخدم: كم سعر دواء Alerid 10mg وما هو استخدامه؟"
    },
    {
        "category": "Database Grounding & Pricing",
        "name": "Contextual Pronoun Question (كم سعره)",
        "type": "generate",
        "prompt": "السياق المستخرج من قاعدة البيانات:\nدواء Alerid 10mg 30 قرص سعره 63.00 ج.م.\n\nسؤال المستخدم: كم سعره وهل هو متوفر؟"
    },
    {
        "category": "Database Grounding & Pricing",
        "name": "Hallucination Test (Unknown Drug)",
        "type": "generate",
        "prompt": "السياق المستخرج من قاعدة البيانات:\nلا توجد نتائج مطابقة لهذا الدواء في المخزون.\n\nسؤال المستخدم: ما سعر دواء SuperCure Max 500mg؟"
    }
]

MULTI_TURN_CONVERSATIONS = [
    {
        "category": "Multi-Turn Memory",
        "name": "Patient Identity & Context Tracking",
        "turns": [
            "أهلاً بك، أنا اسمي أحمد، عمري 45 سنة، وأعاني من ارتفاع ضغط الدم المزمن.",
            "ما هي النصائح العامة لحالتي، وما هو اسمي الذي أخبرتك به؟",
            "ما هو مرضي المزمن وكم عمري؟"
        ]
    }
]

def test_model(model_name):
    print(f"\n==========================================")
    print(f"Testing Model: {model_name}")
    print(f"==========================================")
    results = {"single_turns": [], "multi_turns": []}

    # Warmup
    try:
        requests.post(f"{OLLAMA_API}/generate", json={"model": model_name, "prompt": "hi", "stream": False}, timeout=10)
    except:
        pass

    for tc in TEST_CASES:
        t0 = time.time()
        payload = {
            "model": model_name,
            "prompt": tc["prompt"],
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 250}
        }
        try:
            res = requests.post(f"{OLLAMA_API}/generate", json=payload, timeout=60).json()
            elapsed = time.time() - t0
            response_text = res.get("response", "").strip()
            eval_count = res.get("eval_count", 0)
            eval_dur_s = res.get("eval_duration", 0) / 1e9
            speed = eval_count / eval_dur_s if eval_dur_s > 0 else 0
            
            results["single_turns"].append({
                "category": tc["category"],
                "name": tc["name"],
                "prompt": tc["prompt"],
                "response": response_text,
                "speed": round(speed, 1),
                "elapsed": round(elapsed, 2),
                "eval_count": eval_count
            })
            print(f"  [OK] {tc['name']} ({round(speed, 1)} tok/s, {round(elapsed, 2)}s)")
        except Exception as e:
            results["single_turns"].append({
                "category": tc["category"],
                "name": tc["name"],
                "prompt": tc["prompt"],
                "error": str(e)
            })
            print(f"  [ERR] {tc['name']}: {e}")

    # Multi turn
    for mt in MULTI_TURN_CONVERSATIONS:
        messages = []
        mt_results = {"name": mt["name"], "turns": []}
        for turn_idx, user_msg in enumerate(mt["turns"]):
            messages.append({"role": "user", "content": user_msg})
            payload = {
                "model": model_name,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 250}
            }
            try:
                t0 = time.time()
                res = requests.post(f"{OLLAMA_API}/chat", json=payload, timeout=60).json()
                elapsed = time.time() - t0
                bot_msg = res.get("message", {}).get("content", "").strip()
                eval_count = res.get("eval_count", 0)
                eval_dur_s = res.get("eval_duration", 0) / 1e9
                speed = eval_count / eval_dur_s if eval_dur_s > 0 else 0
                
                messages.append({"role": "assistant", "content": bot_msg})
                mt_results["turns"].append({
                    "turn": turn_idx + 1,
                    "user": user_msg,
                    "bot": bot_msg,
                    "speed": round(speed, 1),
                    "elapsed": round(elapsed, 2)
                })
                print(f"  [OK] Multi-turn #{turn_idx+1} ({round(speed, 1)} tok/s)")
            except Exception as e:
                mt_results["turns"].append({
                    "turn": turn_idx + 1,
                    "user": user_msg,
                    "error": str(e)
                })
                print(f"  [ERR] Multi-turn #{turn_idx+1}: {e}")
        results["multi_turns"].append(mt_results)

    return results

all_results = {}
for m in MODELS:
    all_results[m] = test_model(m)

with open("model_comparison_live.json", "w", encoding="utf-8") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)

print("\nBenchmark completed successfully and saved to model_comparison_live.json")
