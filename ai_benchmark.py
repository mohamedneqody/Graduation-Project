import os
import sys
import json
import time
import subprocess
import requests

OLLAMA_API = "http://localhost:11434/api"

models = ["AI-COS-LFM-Q4:latest", "qwen2.5:3b", "Falcon-H1-Arabic-3B:latest"]

def get_gpu_stats():
    try:
        res = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=utilization.gpu,utilization.memory,memory.used,memory.total", "--format=csv,noheader,nounits"],
            text=True
        ).strip().split(',')
        if len(res) == 4:
            return {
                "gpu_util": float(res[0]),
                "mem_util": float(res[1]),
                "vram_used": float(res[2]),
                "vram_total": float(res[3])
            }
    except Exception:
        pass
    return None

def generate(model, prompt, stream=False, options=None):
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": stream,
        "options": options or {}
    }
    start_time = time.time()
    ttft = None
    token_gaps = []
    generated_text = ""
    
    with requests.post(f"{OLLAMA_API}/generate", json=payload, stream=stream) as r:
        if stream:
            last_token_time = None
            for line in r.iter_lines():
                if line:
                    chunk_time = time.time()
                    data = json.loads(line)
                    if ttft is None:
                        ttft = chunk_time - start_time
                        last_token_time = chunk_time
                    else:
                        token_gaps.append(chunk_time - last_token_time)
                        last_token_time = chunk_time
                    generated_text += data.get("response", "")
                    if data.get("done"):
                        metrics = data
                        break
        else:
            data = r.json()
            generated_text = data.get("response", "")
            metrics = data
            ttft = None
            token_gaps = []
            
    return generated_text, metrics, ttft, token_gaps

def chat(model, messages, options=None):
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": options or {}
    }
    r = requests.post(f"{OLLAMA_API}/chat", json=payload)
    return r.json()

results = {}

for model in models:
    print(f"Testing {model}...")
    results[model] = {}
    
    # Pre-load model to get steady state VRAM
    requests.post(f"{OLLAMA_API}/generate", json={"model": model, "prompt": "hi", "stream": False})
    time.sleep(2)
    gpu_initial = get_gpu_stats()
    
    # Phase 4: Speed
    speed_runs = []
    prompt = "اشرح لي الفرق بين الذكاء الاصطناعي وتعلم الآلة والتعلم العميق، واذكر مثالًا عمليًا بسيطًا على كل واحد."
    for i in range(2): # 2 runs to save time, prompt is exact
        _, metrics, _, _ = generate(model, prompt, stream=False, options={"temperature": 0, "seed": 42, "num_predict": 100})
        speed_runs.append(metrics)
    results[model]['speed'] = speed_runs
    
    gpu_active = get_gpu_stats()
    results[model]['vram_used'] = gpu_active['vram_used'] if gpu_active else 0
    results[model]['gpu_util'] = gpu_active['gpu_util'] if gpu_active else 0
    
    # Phase 5: Streaming
    _, _, ttft, gaps = generate(model, prompt, stream=True, options={"temperature": 0, "seed": 42, "num_predict": 100})
    results[model]['streaming'] = {'ttft': ttft, 'gaps': gaps}
    
    # Phase 6: Long Generation
    long_prompt = "اشرح بالتفصيل كيف تعمل الشبكات العصبية، بدءًا من المدخلات ثم الأوزان ثم دالة التنشيط ثم الـforward pass ثم loss ثم backpropagation، مع مثال مبسط."
    long_text, long_metrics, _, _ = generate(model, long_prompt, stream=False, options={"temperature": 0, "num_predict": 200})
    results[model]['long'] = {'text': long_text, 'metrics': long_metrics}
    
    # Phase 7: Arabic Chat (1 sample to save time, evaluate visually)
    chat_prompt = "لدي صداع نصفي متكرر وأتناول دواء مسكن. متى يجب أن أزور الطبيب؟"
    chat_text, _, _, _ = generate(model, chat_prompt, stream=False, options={"temperature": 0.2})
    results[model]['arabic'] = chat_text
    
    # Phase 8: Memory
    messages = []
    turns = [
        ("اسمي أحمد.", "أهلاً أحمد"),
        ("أنا أعمل في مشروع تخرج.", "بالتوفيق في مشروع التخرج"),
        ("ما اسمي؟", ""),
        ("ماذا أعمل؟", "")
    ]
    mem_responses = []
    for user_msg, expected in turns:
        messages.append({"role": "user", "content": user_msg})
        resp = chat(model, messages, options={"temperature": 0})
        bot_msg = resp.get("message", {}).get("content", "")
        mem_responses.append(bot_msg)
        messages.append({"role": "assistant", "content": bot_msg})
    results[model]['memory'] = mem_responses

with open("benchmark_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("Done")
