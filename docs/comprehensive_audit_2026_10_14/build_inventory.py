"""Inventory source snapshot and locally exported n8n metadata; no credentials emitted."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
paths = [ROOT/'AI-COS-Pharmacy/backend/app', ROOT/'AI-COS-Pharmacy/backend/tests',
         ROOT/'AI-COS-Pharmacy/backend/alembic', ROOT/'AI-COS-Pharmacy/backend/migrations',
         ROOT/'AI-COS-Pharmacy/frontend/src', ROOT/'upload']
files=[]
for root in paths:
    for p in sorted(root.rglob('*')):
        if not p.is_file() or p.suffix not in {'.py','.ts','.tsx','.sql','.yaml'}:
            continue
        if any(s in p.parts for s in ('__pycache__','node_modules','.venv')):
            continue
        data=p.read_bytes()
        content=data.decode('utf-8-sig',errors='replace')
        row={'path':p.relative_to(ROOT).as_posix(),'lines':len(content.splitlines()),
             'sha256':hashlib.sha256(data).hexdigest()}
        if p.suffix=='.py':
            try:
                tree=ast.parse(content)
                row['functions']=sum(isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) for n in ast.walk(tree))
            except SyntaxError as e:
                row['syntax_error_line']=e.lineno
        files.append(row)

workflows=[]
for dirname in ('N8N','n8n final','n8n_w15','9 وكلاء'):
    for p in sorted((ROOT/dirname).rglob('*.json')):
        if 'node_modules' in p.parts:
            continue
        try:
            data=json.loads(p.read_text(encoding='utf-8-sig'))
            nodes=data.get('nodes',[]) if isinstance(data,dict) else []
            if not nodes: continue
            workflows.append({'path':p.relative_to(ROOT).as_posix(),
              'export_active_flag':data.get('active'), 'node_count':len(nodes),
              'node_types':sorted(set(n.get('type','') for n in nodes)),
              'webhook_auth_modes':[n.get('parameters',{}).get('authentication','not_declared')
                for n in nodes if n.get('type','').endswith('.webhook')],
              'sql_nodes_with_tenant_reference':sum('tenant' in str(n.get('parameters',{})).lower()
                 for n in nodes if 'postgres' in n.get('type','').lower()),
              'postgres_nodes':sum('postgres' in n.get('type','').lower() for n in nodes)})
        except (ValueError,OSError): pass

out={'source_files':files,'n8n_exports':workflows}
Path(__file__).with_name('source_inventory.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'files':len(files),'lines':sum(f['lines'] for f in files),
   'python_syntax_errors':[f for f in files if 'syntax_error_line' in f],
   'n8n_exports':len(workflows),
   'largest_files':sorted(files,key=lambda f:-f['lines'])[:8]},ensure_ascii=True,indent=2))
