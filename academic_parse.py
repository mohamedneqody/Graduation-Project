import json
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('academic_benchmark.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

for model, data in d.items():
    print(f"\\n{'='*50}\\nMODEL: {model}\\n{'='*50}")
    
    phases = data.get("phases", {})
    gpu_d = data.get("gpu_dataset", {})
    gpu_s = data.get("gpu_speed", {})
    leaks = data.get("total_think_leaks", 0)
    
    print(f"[GPU INFO] Avg Util: {gpu_d.get('avg_gpu', 0)}%, Max VRAM: {gpu_d.get('max_vram', 0)} MB")
    print(f"[THINK LEAKS] Total occurrences: {leaks}")
    
    # Speed
    speed_runs = phases.get("speed", [])
    if speed_runs:
        ttft = sum(s["ttft"] for s in speed_runs)/len(speed_runs)
        toks = sum(s["speed"] for s in speed_runs)/len(speed_runs)
        print(f"[SPEED] Avg TTFT: {ttft:.3f}s, Avg Tok/s: {toks:.1f}")
        
    # Instruction
    print("\\n[INSTRUCTION FOLLOWING]")
    for item in phases.get("instruction", []):
        ans = item['output'].replace('\\n', ' ')[:60]
        print(f"  - {item['type']}: {ans}...")
        
    # RAG & Hallucination
    print("\\n[RAG & HALLUCINATION]")
    for item in phases.get("rag", []):
        ans = item['output'].replace('\\n', ' ')[:60]
        print(f"  - {item['type']}: {ans}...")
        
    # Memory
    print("\\n[DEEP MEMORY]")
    mem = phases.get("memory", [])
    if len(mem) >= 4:
        print(f"  - Turn 4 (Name/Age): {mem[3]['bot'].replace('\\n', ' ')[:60]}...")
        print(f"  - Turn 5 (Job/Loc): {mem[4]['bot'].replace('\\n', ' ')[:60]}...")
        print(f"  - Turn 6 (Drink): {mem[5]['bot'].replace('\\n', ' ')[:60]}...")
        print(f"  - Turn 7 (Summary): {mem[6]['bot'].replace('\\n', ' ')[:60]}...")
        
    # Arabic Chat
    print("\\n[ARABIC CHAT]")
    for item in phases.get("arabic", []):
        ans = item['output'].replace('\\n', ' ')[:50]
        print(f"  - {item['type']}: {ans}...")
