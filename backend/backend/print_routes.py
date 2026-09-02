from app.main import app
for r in app.routes:
    if hasattr(r, 'methods'):
        if 'contact' in getattr(r, 'path', ''):
            print(f'{r.methods} {r.path}')
