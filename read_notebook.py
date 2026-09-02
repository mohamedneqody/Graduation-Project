import json

path = r'D:\مشروع تخرج\تدريب_LFM2_5_(1) (7).ipynb'
with open(path, 'r', encoding='utf-8') as f:
    nb = json.load(f)
    print(f"Total cells: {len(nb.get('cells', []))}")
    for i, cell in enumerate(nb.get('cells', [])):
        if cell['cell_type'] == 'code':
            source = ''.join(cell.get('source', []))
            print(f"\n--- Cell {i} (Code) ---\n{source[:500]}\n")
        elif cell['cell_type'] == 'markdown':
            source = ''.join(cell.get('source', []))
            print(f"\n--- Cell {i} (Markdown) ---\n{source[:200]}\n")
