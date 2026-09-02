import os
import sys
import json
import time
import subprocess
import requests
import threading

OLLAMA_API = "http://localhost:11434/api"
MODELS = ["AI-COS-Qwen-2.5:latest", "AI-COS-LFM-Q4:latest"]
RESULTS = {}

# GPU Monitor
gpu_stats_log = []
stop_gpu = False

def monitor_gpu():
    while not stop_gpu:
        try:
            res = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=utilization.gpu,utilization.memory,memory.used,memory.total", "--format=csv,noheader,nounits"],
                text=True
            ).strip().split(',')
            if len(res) == 4:
                gpu_stats_log.append({
                    "gpu": float(res[0]),
                    "vram": float(res[2])
                })
        except:
            pass
        time.sleep(1)

def get_avg_gpu():
    if not gpu_stats_log: return 0, 0
    avg_gpu = sum(x["gpu"] for x in gpu_stats_log) / len(gpu_stats_log)
    max_vram = max(x["vram"] for x in gpu_stats_log)
    return avg_gpu, max_vram

def generate(model, prompt, stream=False, options=None):
    payload = {"model": model, "prompt": prompt, "stream": stream, "options": options or {}}
    start_time = time.time()
    ttft = None
    gaps = []
    text = ""
    metrics = {}
    
    try:
        with requests.post(f"{OLLAMA_API}/generate", json=payload, stream=stream) as r:
            if stream:
                last_time = None
                for line in r.iter_lines():
                    if line:
                        chunk_time = time.time()
                        data = json.loads(line)
                        if ttft is None:
                            ttft = chunk_time - start_time
                        elif last_time:
                            gaps.append(chunk_time - last_time)
                        last_time = chunk_time
                        text += data.get("response", "")
                        if data.get("done"):
                            metrics = data
                            break
            else:
                data = r.json()
                text = data.get("response", "")
                metrics = data
    except Exception as e:
        print(f"Error generation: {e}")
        
    return text, metrics, ttft, gaps

def chat(model, messages, options=None):
    payload = {"model": model, "messages": messages, "stream": False, "options": options or {}}
    r = requests.post(f"{OLLAMA_API}/chat", json=payload)
    return r.json().get("message", {}).get("content", "")

# Load Validation Data
val_data = []
try:
    with open("validation.jsonl", "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= 50: break
            d = json.loads(line)
            sys_msg = next((m['content'] for m in d['messages'] if m['role']=='system'), "")
            user_msg = next((m['content'] for m in d['messages'] if m['role']=='user'), "")
            ast_msg = next((m['content'] for m in d['messages'] if m['role']=='assistant'), "")
            val_data.append({"sys": sys_msg, "user": user_msg, "expected": ast_msg})
except Exception as e:
    print(f"Dataset error: {e}")

gpu_thread = threading.Thread(target=monitor_gpu)
gpu_thread.start()

for model in MODELS:
    print(f"\\n--- Testing {model} ---")
    RESULTS[model] = {}
    
    # Warmup
    generate(model, "hi", False, {"num_predict": 10})
    time.sleep(1)
    
    # Phase 2: Speed
    print("Phase 2: Speed")
    speed_runs = []
    gpu_stats_log.clear()
    prompt_speed = "اشرح لي الفرق بين الذكاء الاصطناعي وتعلم الآلة والتعلم العميق، واذكر مثالًا عمليًا على كل واحد."
    for _ in range(5):
        _, m, _, _ = generate(model, prompt_speed, False, {"temperature": 0, "seed": 42, "num_predict": 100})
        speed_runs.append(m)
    avg_gpu, max_vram = get_avg_gpu()
    RESULTS[model]['speed'] = speed_runs
    RESULTS[model]['gpu'] = {"util": avg_gpu, "vram": max_vram}
    
    # Phase 3: Streaming
    print("Phase 3: Streaming")
    _, _, ttft, gaps = generate(model, prompt_speed, True, {"temperature": 0, "seed": 42, "num_predict": 100})
    RESULTS[model]['streaming'] = {'ttft': ttft, 'gaps': gaps}
    
    # Phase 4: Dataset
    print(f"Phase 4: Dataset ({len(val_data)} samples)")
    ds_results = []
    for d in val_data:
        messages = [{"role": "system", "content": d["sys"]}, {"role": "user", "content": d["user"]}]
        out = chat(model, messages, {"temperature": 0, "num_predict": 150})
        ds_results.append({"user": d["user"], "expected": d["expected"], "output": out})
    RESULTS[model]['dataset'] = ds_results
    
    # Phase 5: Arabic Chat
    print("Phase 5: Arabic")
    ar_prompts = [
        "ما هي عاصمة مصر؟",
        "ليه الجو حر جدا في الصيف ده في القاهرة؟",
        "اكتب لي خطة قصيرة من 3 خطوات لتعلم البرمجة.",
        "لخص لي فوائد النوم المبكر في سطر واحد.",
        "هل الدواء سحري ويمكنه علاج كل شيء فوراً؟"
    ]
    ar_res = []
    for p in ar_prompts:
        txt, _, _, _ = generate(model, p, False, {"temperature": 0.2})
        ar_res.append(txt)
    RESULTS[model]['arabic'] = ar_res
    
    # Phase 6: Memory
    print("Phase 6: Memory")
    mem_msgs = []
    mem_turns = [
        ("اسمي أحمد.", ""),
        ("أعمل على مشروع تخرج.", ""),
        ("أدرس نظم معلومات الأعمال.", ""),
        ("ما اسمي؟", ""),
        ("ماذا أعمل؟", ""),
        ("ماذا أدرس؟", "")
    ]
    mem_out = []
    for u, _ in mem_turns:
        mem_msgs.append({"role": "user", "content": u})
        ans = chat(model, mem_msgs, {"temperature": 0})
        mem_out.append(ans)
        mem_msgs.append({"role": "assistant", "content": ans})
    RESULTS[model]['memory'] = mem_out
    
    # Phase 7: RAG
    print("Phase 7: RAG")
    rag_sys = "المنتج A يستخدم للحالة X. يجب تجنب المنتج A في الحالة Y. المنتج B يستخدم للحالة Z."
    r1 = chat(model, [{"role": "system", "content": rag_sys}, {"role": "user", "content": "ما استخدام المنتج A وما الحالة التي يجب تجنبها؟"}])
    r2 = chat(model, [{"role": "system", "content": rag_sys}, {"role": "user", "content": "ما سعر المنتج A؟"}])
    RESULTS[model]['rag'] = [r1, r2]
    
    # Phase 8: Long Response
    print("Phase 8: Long")
    long_p = "اشرح بالتفصيل كيف تعمل الشبكات العصبية من المدخلات إلى forward pass ثم loss ثم backpropagation، مع مثال مبسط."
    l_txt, l_m, _, _ = generate(model, long_p, False, {"temperature": 0, "num_predict": 200})
    RESULTS[model]['long'] = {"text": l_txt, "metrics": l_m}

stop_gpu = True
gpu_thread.join()

with open("final_benchmark.json", "w", encoding="utf-8") as f:
    json.dump(RESULTS, f, ensure_ascii=False, indent=2)
print("Done!")
