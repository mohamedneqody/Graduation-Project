import json
with open('intel_test.json', 'r', encoding='utf-8') as f:
    d = json.load(f)
for m in d:
    print(f"\nModel: {m}")
    for q in d[m]:
        print(f"  Q: {q}")
        ans = d[m][q]["answer"].replace('\n', ' ')
        print(f"  A: {ans[:90]}...")
        print(f"  Speed: {d[m][q]['speed']} tok/s")
