import json
import os

file_path = r'D:\Graduation Project\ai models\تدريب_LFM2_5.ipynb'

with open(file_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Clear all outputs
for cell in nb.get('cells', []):
    if 'outputs' in cell:
        cell['outputs'] = []
    if 'execution_count' in cell:
        cell['execution_count'] = None

cells = nb.get('cells', [])
new_cells = []

for i, cell in enumerate(cells):
    if cell['cell_type'] == 'code':
        source = cell['source']
        src_str = ''.join(source)
        
        # 1. HuggingFace Login addition (after the first print torch cell)
        if 'torch.cuda.get_device_name' in src_str:
            new_cells.append(cell)
            new_cells.append({
                'cell_type': 'code',
                'metadata': {},
                'execution_count': None,
                'outputs': [],
                'source': [
                    '# Login to Hugging Face to access gated models (like Liquid AI LFM)\n',
                    'from huggingface_hub import notebook_login\n',
                    'notebook_login()'
                ]
            })
            continue

        # 2. Add trust_remote_code=True
        if 'AutoModelForCausalLM.from_pretrained' in src_str:
            src_str = src_str.replace('tokenizer = AutoTokenizer.from_pretrained(model_name)', 'tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)')
            src_str = src_str.replace('torch_dtype=torch.bfloat16,', 'torch_dtype=torch.bfloat16,\n    trust_remote_code=True,')
            cell['source'] = [src_str]
        
        # 3. Fix LoRA target_modules
        if 'target_modules=[' in src_str and '"o_proj"' in src_str:
            src_str = src_str.replace('"o_proj"', '"out_proj"')
            # Add MLP and conv proj layers for better adaptation
            src_str = src_str.replace('"out_proj",', '"out_proj",\n        "w1",\n        "w2",\n        "w3",\n        "in_proj",')
            cell['source'] = [src_str]

        # 4. Fix SFTConfig arguments
        if 'SFTConfig(' in src_str:
            src_str = src_str.replace('max_length=2048', 'max_seq_length=2048')
            # Add explicit dataset text field and gradient checkpointing
            src_str = src_str.replace('report_to="none",', 'report_to="none",\n    dataset_text_field="text",\n    gradient_checkpointing=True,')
            cell['source'] = [src_str]

    new_cells.append(cell)

nb['cells'] = new_cells

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=2, ensure_ascii=False)

print('Notebook updated successfully.')
