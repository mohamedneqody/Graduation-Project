import requests
import time

url_hf = 'https://huggingface.co/tiiuae/Falcon-H1-3B-Instruct-GGUF/resolve/main/Falcon-H1-3B-Instruct-Q4_K_M.gguf'
url_mirror = 'https://hf-mirror.com/tiiuae/Falcon-H1-3B-Instruct-GGUF/resolve/main/Falcon-H1-3B-Instruct-Q4_K_M.gguf'

def get_metadata(url):
    try:
        h = requests.head(url, allow_redirects=True, timeout=10)
        size = int(h.headers.get('content-length', 0))
        sha256 = h.headers.get('x-linked-etag', '').strip('"')
        return size, sha256
    except Exception as e:
        print(f"Error fetching metadata for {url}: {e}")
        return 0, ""

def test_speed(url, name):
    try:
        print(f"Testing {name}...")
        start = time.time()
        r = requests.get(url, stream=True, timeout=10)
        downloaded = 0
        chunk_size = 8192
        # Download ~5 MB to test speed
        target = 5 * 1024 * 1024
        for chunk in r.iter_content(chunk_size):
            if chunk:
                downloaded += len(chunk)
            if downloaded >= target:
                break
            if time.time() - start > 15: # max 15 seconds test
                break
        duration = time.time() - start
        speed_kb = (downloaded / 1024) / duration
        speed_mb = speed_kb / 1024
        print(f"[{name}] Downloaded: {downloaded/1024/1024:.2f} MB in {duration:.2f}s | Speed: {speed_mb:.2f} MB/s ({speed_kb:.2f} KB/s)")
    except Exception as e:
        print(f"[{name}] Error: {e}")

size_hf, sha_hf = get_metadata(url_hf)
print(f"Official HF - Size: {size_hf / (1024**3):.2f} GB, SHA256: {sha_hf}")

size_mirror, sha_mirror = get_metadata(url_mirror)
print(f"HF Mirror - Size: {size_mirror / (1024**3):.2f} GB, SHA256: {sha_mirror}")

if size_hf > 0:
    test_speed(url_hf, "Official HuggingFace Direct Download")
if size_mirror > 0:
    test_speed(url_mirror, "HF-Mirror (hf-mirror.com)")
