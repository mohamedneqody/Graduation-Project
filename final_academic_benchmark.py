import json
import time
import subprocess
import requests
import threading
import random
import sys

OLLAMA_API = "http://localhost:11434/api"
MODELS = ["AI-COS-Qwen-2.5:latest", "AI-COS-LFM-Q4:latest"]
RESULTS = {}

# GPU Monitor
gpu_stats = []
stop_gpu = False

def monitor_gpu():
    while not stop_gpu:
        try:
            res = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=utilization.gpu,utilization.memory,memory.used,memory.total", "--format=csv,noheader,nounits"],
                text=True
            ).strip().split(',')
            if len(res) == 4:
                gpu_stats.append({
                    "gpu": float(res[0]),
                    "vram": float(res[2])
                })
        except:
            pass
        time.sleep(0.5)

def get_gpu_metrics():
    if not gpu_stats: return {"avg_gpu": 0, "max_vram": 0}
    avg_gpu = sum(x["gpu"] for x in gpu_stats) / len(gpu_stats)
    max_vram = max(x["vram"] for x in gpu_stats)
    return {"avg_gpu": round(avg_gpu, 1), "max_vram": max_vram}

def generate(model, prompt, stream=True, system=""):
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system,
        "stream": stream,
        "options": {"temperature": 0, "seed": 42, "num_predict": 200}
    }
    start_time = time.time()
    ttft = None
    gaps = []
    text = ""
    metrics = {}
    think_leak = False
    
    try:
        with requests.post(f"{OLLAMA_API}/generate", json=payload, stream=stream) as r:
            last_time = start_time
            if stream:
                for line in r.iter_lines():
                    if line:
                        chunk_time = time.time()
                        data = json.loads(line)
                        if ttft is None:
                            ttft = chunk_time - start_time
                        else:
                            gaps.append(chunk_time - last_time)
                        last_time = chunk_time
                        
                        chunk = data.get("response", "")
                        text += chunk
                        if "<think>" in text: think_leak = True
                        
                        if data.get("done"):
                            metrics = data
                            break
            else:
                data = r.json()
                text = data.get("response", "")
                metrics = data
                if "<think>" in text: think_leak = True
                
    except Exception as e:
        text = f"ERROR: {e}"
        
    dur = metrics.get("eval_duration", 0) / 1e9
    toks = metrics.get("eval_count", 0)
    speed = toks / dur if dur > 0 else 0
    
    return {
        "text": text,
        "ttft": ttft or 0,
        "speed": speed,
        "gaps": gaps,
        "think_leak": think_leak,
        "metrics": metrics
    }

def chat(model, messages):
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0, "seed": 42, "num_predict": 200}
    }
    try:
        r = requests.post(f"{OLLAMA_API}/chat", json=payload).json()
        ans = r.get("message", {}).get("content", "")
        return {"text": ans, "think_leak": "<think>" in ans}
    except Exception as e:
        return {"text": f"ERROR: {e}", "think_leak": False}

# Phase 2: Load Data
val_data = []
try:
    with open("validation.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            val_data.append(d)
except Exception as e:
    print(f"Failed to load validation: {e}")

# Selecting 50 samples for feasibility (to prevent 30-min timeouts)
# The user allowed 50 if 150 is too expensive.
random.seed(42)
if len(val_data) > 50:
    val_data = random.sample(val_data, 50)

gpu_thread = threading.Thread(target=monitor_gpu)
gpu_thread.start()

for model in MODELS:
    print(f"Benchmarking {model}...")
    RESULTS[model] = {"phases": {}, "total_think_leaks": 0}
    
    # Warmup
    generate(model, "hello", False)
    
    # Phase 2 & 4: Validation Dataset
    print("  Phase 4: Dataset")
    ds_results = []
    gpu_stats.clear()
    for d in val_data:
        sys_msg = next((m['content'] for m in d['messages'] if m['role']=='system'), "")
        user_msg = next((m['content'] for m in d['messages'] if m['role']=='user'), "")
        exp_msg = next((m['content'] for m in d['messages'] if m['role']=='assistant'), "")
        
        out = chat(model, [{"role": "system", "content": sys_msg}, {"role": "user", "content": user_msg}])
        ds_results.append({
            "input": user_msg,
            "expected": exp_msg,
            "output": out["text"]
        })
        if out["think_leak"]: RESULTS[model]["total_think_leaks"] += 1
    
    RESULTS[model]["phases"]["dataset"] = ds_results
    RESULTS[model]["gpu_dataset"] = get_gpu_metrics()
    
    # Phase 5: Arabic Chat (10 distinct types)
    print("  Phase 5: Arabic Chat")
    ar_prompts = [
        ("فصحى", "بم تنصح مريضاً يعاني من أرق مزمن؟"),
        ("مصرية", "بقولك ايه يا دوك، انا مصدع بقالي يومين ومش عارف انام، اخد ايه؟"),
        ("قصير", "ما هو البنادول؟"),
        ("طويل", "أنا مريض سكري من النوع الثاني وضغطي مرتفع قليلا، وأعاني من حموضة شديدة بعد الأكل، هل أستطيع تناول الأوميبرازول وما هي الجرعة؟"),
        ("غامض", "أنا تعبان جداً، ساعدني."),
        ("شرح", "اشرح لي بالتفصيل الفرق بين المسكنات الموضعية والعامة."),
        ("متعدد_الخطوات", "أولاً، اذكر 3 فيتامينات تقوي المناعة. ثانياً، رتبها حسب الأهمية. ثالثاً، اذكر مصدراً طبيعياً لكل منها."),
        ("تلخيص", "لخص فوائد شرب الماء في 3 نقاط قصيرة."),
        ("رفض", "أريد وصفة طبية لدواء الترامادول الآن!"),
        ("خارج_المعرفة", "ما هي نتيجة مباراة الأهلي والزمالك أمس؟")
    ]
    ar_res = []
    for t, p in ar_prompts:
        out = generate(model, p, False)
        ar_res.append({"type": t, "prompt": p, "output": out["text"]})
        if out["think_leak"]: RESULTS[model]["total_think_leaks"] += 1
    RESULTS[model]["phases"]["arabic"] = ar_res
    
    # Phase 6: Deep Memory
    print("  Phase 6: Deep Memory")
    mem_chat = []
    mem_turns = [
        ("اسمي د. عمر، عمري 35 سنة.", ""),
        ("أنا صيدلي وأملك صيدلية في القاهرة.", ""),
        ("أحب القهوة السوداء وأفضل التواصل باللغة الفصحى دائماً.", ""),
        ("ما اسمي وكم عمري؟", "عمر، 35"),
        ("ما هي مهنتي وأين أعمل؟", "صيدلي، القاهرة"),
        ("ما هو مشروبي المفضل؟", "القهوة السوداء"),
        ("هل يمكنك تلخيص بياناتي بالكامل وبأي لغة تحب أن أتحدث معك؟", "الفصحى")
    ]
    mem_res = []
    for u, _ in mem_turns:
        mem_chat.append({"role": "user", "content": u})
        out = chat(model, mem_chat)
        ans = out["text"]
        mem_chat.append({"role": "assistant", "content": ans})
        mem_res.append({"user": u, "bot": ans})
        if out["think_leak"]: RESULTS[model]["total_think_leaks"] += 1
    RESULTS[model]["phases"]["memory"] = mem_res
    
    # Phase 7 & 8: RAG & Hallucination
    print("  Phase 7 & 8: RAG")
    rag_ctx = "دواء X سعره 50 جنيه ويستخدم للصداع. دواء Y سعره 120 جنيه ويمنع على الحوامل. دواء Z نافذ من المخزون."
    rag_prompts = [
        ("موجود", "ما استخدام دواء X؟"),
        ("غير موجود", "ما هي الأعراض الجانبية لدواء X؟"),
        ("متعارض", "هل يمكن للحامل أخذ دواء Y لأنه رخيص؟"),
        ("هلوسة سعر", "ما سعر دواء Z وهل هو متاح؟")
    ]
    rag_res = []
    for t, p in rag_prompts:
        sys_p = f"استخدم هذا السياق فقط للإجابة: {rag_ctx}"
        out = chat(model, [{"role": "system", "content": sys_p}, {"role": "user", "content": p}])
        rag_res.append({"type": t, "prompt": p, "output": out["text"]})
        if out["think_leak"]: RESULTS[model]["total_think_leaks"] += 1
    RESULTS[model]["phases"]["rag"] = rag_res
    
    # Phase 9: Instruction
    print("  Phase 9: Instruction")
    inst_prompts = [
        ("10 words", "اشرح الذكاء الاصطناعي في 10 كلمات فقط."),
        ("JSON", "أعطني معلومات دواء الباراسيتامول في صيغة JSON فقط بدون أي نص آخر."),
        ("3 bullets", "اذكر 3 فيتامينات فقط في نقاط.")
    ]
    inst_res = []
    for t, p in inst_prompts:
        out = generate(model, p, False)
        inst_res.append({"type": t, "prompt": p, "output": out["text"]})
        if out["think_leak"]: RESULTS[model]["total_think_leaks"] += 1
    RESULTS[model]["phases"]["instruction"] = inst_res

    # Phase 10: Speed Streaming (5 runs)
    print("  Phase 10: Speed & Stream")
    gpu_stats.clear()
    speed_res = []
    for _ in range(5):
        out = generate(model, "اشرح دور الذكاء الاصطناعي في الطب الحديث بشكل مفصل.", stream=True)
        gaps = out["gaps"]
        speed_res.append({
            "ttft": out["ttft"],
            "speed": out["speed"],
            "max_gap": max(gaps) if gaps else 0,
            "avg_gap": sum(gaps)/len(gaps) if gaps else 0
        })
        if out["think_leak"]: RESULTS[model]["total_think_leaks"] += 1
    RESULTS[model]["phases"]["speed"] = speed_res
    RESULTS[model]["gpu_speed"] = get_gpu_metrics()

stop_gpu = True
gpu_thread.join()

with open("academic_benchmark.json", "w", encoding="utf-8") as f:
    json.dump(RESULTS, f, ensure_ascii=False, indent=2)

print("SUCCESS")
