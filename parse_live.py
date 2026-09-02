import json
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('model_comparison_live.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

for m, data in d.items():
    print(f"\n{'='*60}\nMODEL: {m}\n{'='*60}")
    for item in data.get('single_turns', []):
        print(f"\n>>> [{item['category']}] - {item['name']}")
        print(f"Speed: {item['speed']} tok/s | Elapsed: {item['elapsed']}s")
        print(f"Q: {item['prompt']}")
        print(f"A: {item['response']}")
        print("-" * 50)
    
    print("\n>>> [MULTI-TURN MEMORY TEST]")
    for mt in data.get('multi_turns', []):
        for turn in mt['turns']:
            print(f"User ({turn['turn']}): {turn['user']}")
            print(f"Bot  ({turn['turn']}): {turn.get('bot', '')}")
            print()
