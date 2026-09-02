import time
import requests
import sys
sys.stdout.reconfigure(encoding='utf-8')
from sentence_transformers import SentenceTransformer

print("Loading BERT model locally...")
start_load = time.time()
encoder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
print(f"BERT model loaded in {time.time() - start_load:.2f} seconds.\n")

questions = [
    "اهلا",
    "ما هو سعر دواء alerid 10 mg؟",
    "من قام بصناعتك؟"
]

print("=== Benchmarking BERT (Local Embeddings) ===")
for q in questions:
    start_time = time.time()
    vec = encoder.encode(q)
    end_time = time.time()
    print(f"Query: '{q}'")
    print(f"BERT Embedding Time: {(end_time - start_time) * 1000:.2f} ms\n")


print("=== Benchmarking Qwen (Local Generative) ===")
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "AI-COS-Qwen-2.5:latest"

for q in questions:
    start_time = time.time()
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": q,
            "stream": False
        }, timeout=30.0)
        
        end_time = time.time()
        print(f"Query: '{q}'")
        if resp.status_code == 200:
            print(f"Qwen Generation Time: {(end_time - start_time) * 1000:.2f} ms")
        else:
            print(f"Qwen Failed: {resp.status_code}")
    except Exception as e:
        print(f"Qwen Error: {e}")
    print("\n")
