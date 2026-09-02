import requests
import time
import threading

url = 'https://huggingface.co/tiiuae/Falcon-H1-3B-Instruct-GGUF/resolve/main/Falcon-H1-3B-Instruct-Q4_K_M.gguf'

downloaded = 0
running = True

def download_chunk(start, end):
    global downloaded, running
    headers = {'Range': f'bytes={start}-{end}'}
    try:
        r = requests.get(url, headers=headers, stream=True, timeout=10)
        for chunk in r.iter_content(8192):
            if not running:
                break
            if chunk:
                downloaded += len(chunk)
    except:
        pass

threads = []
# 8 concurrent connections
chunk_size = 5 * 1024 * 1024
for i in range(8):
    t = threading.Thread(target=download_chunk, args=(i*chunk_size, (i+1)*chunk_size - 1))
    t.start()
    threads.append(t)

print("Testing Multi-threaded speed...")
start = time.time()
while time.time() - start < 15:
    time.sleep(1)
running = False

for t in threads:
    t.join()

duration = time.time() - start
speed_mb = (downloaded / 1024 / 1024) / duration
print(f"Multi-threaded Downloaded: {downloaded/1024/1024:.2f} MB in {duration:.2f}s | Speed: {speed_mb:.2f} MB/s")
