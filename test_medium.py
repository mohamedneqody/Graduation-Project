import urllib.request
import os

file_path = r'D:\Graduation Project\AI-COS-Pharmacy\backend\tests\benchmark_images\diff_medium_01.png'
with open(file_path, 'rb') as f:
    file_data = f.read()

boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
body = b'--' + boundary.encode() + b'\r\n' + b'Content-Disposition: form-data; name=\"file\"; filename=\"1.png\"\r\nContent-Type: image/png\r\n\r\n' + file_data + b'\r\n--' + boundary.encode() + b'--\r\n'

secret = 'secret'
env = r'D:\Graduation Project\AI-COS-Pharmacy\backend\.env'
if os.path.exists(env):
    for line in open(env, encoding='utf-8'):
        if line.startswith('INTERNAL_OCR_SECRET='):
            secret = line.split('=')[1].strip().strip('\"\'')

req = urllib.request.Request('http://127.0.0.1:9202/api/infer-text', data=body, headers={'x-internal-secret': secret, 'Content-Type': 'multipart/form-data; boundary=' + boundary})

import urllib.error
try:
    print(urllib.request.urlopen(req).read().decode())
except urllib.error.HTTPError as e:
    print('HTTP ERROR:', e.read().decode())
except Exception as e:
    print('OTHER ERROR:', e)
