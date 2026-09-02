import asyncio
import httpx
import uvicorn
from multiprocessing import Process
import time

def run_server():
    uvicorn.run('app.main:app', host='127.0.0.1', port=8000, log_level='debug')

if __name__ == '__main__':
    p = Process(target=run_server)
    p.start()
    time.sleep(4)
    try:
        r = httpx.get('http://127.0.0.1:8000/health', timeout=3)
        print('HEALTH:', r.status_code, r.text)
    except Exception as e:
        print('ERROR:', e)
    finally:
        p.terminate()
