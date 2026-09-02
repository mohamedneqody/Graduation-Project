import json

def analyze():
    with open('final_benchmark.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    for m in data:
        print(f"\\n{'='*40}")
        print(f"MODEL: {m}")
        print(f"{'='*40}")
        
        gpu = data[m].get("gpu", {})
        print(f"GPU VRAM Used : {gpu.get('vram', 0):.0f} MiB")
        print(f"GPU Util      : {gpu.get('util', 0):.1f}%")
        
        speeds = data[m].get('speed', [])
        if speeds:
            valid_speeds = [s for s in speeds if s.get('eval_duration', 0) > 0]
            if valid_speeds:
                ttft = sum(s.get('prompt_eval_duration', 0)/1e9 for s in valid_speeds)/len(valid_speeds)
                toks = sum(s.get('eval_count', 0) / (s.get('eval_duration', 1)/1e9) for s in valid_speeds)/len(valid_speeds)
                ms_tok = (1 / toks) * 1000 if toks > 0 else 0
                print(f"Speed         : TTFT {ttft:.2f}s | {toks:.1f} tok/s | {ms_tok:.1f} ms/tok")
        
        stream = data[m].get('streaming', {})
        gaps = stream.get('gaps', [])
        if gaps:
            print(f"Streaming     : Avg gap {sum(gaps)/len(gaps):.3f}s | Max gap {max(gaps):.3f}s")
            
        ds = data[m].get('dataset', [])
        print(f"Dataset Evals : {len(ds)} samples")
        
        ar = data[m].get('arabic', [])
        print(f"Arabic 1 (Capital): {ar[0][:50].replace(chr(10), ' ')}")
        print(f"Arabic 5 (Magic Med): {ar[4][:50].replace(chr(10), ' ')}")
        
        mem = data[m].get('memory', [])
        print(f"Memory (Name): {mem[3][:50].replace(chr(10), ' ')}")
        print(f"Memory (Work): {mem[4][:50].replace(chr(10), ' ')}")
        print(f"Memory (Study): {mem[5][:50].replace(chr(10), ' ')}")
        
        rag = data[m].get('rag', [])
        print(f"RAG (Q1 Use/Avoid): {rag[0][:60].replace(chr(10), ' ')}")
        print(f"RAG (Q2 Price Null): {rag[1][:60].replace(chr(10), ' ')}")
        
        long = data[m].get('long', {})
        print(f"Long Resp Length: {len(long.get('text', ''))} chars")

analyze()
