import psutil
import time
import subprocess
import os

print("Killing uvicorn processes...")
killed = False
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if proc.info['name'] in ['python.exe', 'uvicorn.exe']:
            cmd = proc.info.get('cmdline', [])
            if cmd and 'uvicorn' in ' '.join(cmd).lower():
                print(f"Killing PID {proc.info['pid']}: {cmd}")
                proc.kill()
                killed = True
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

if killed:
    print("Waiting 2 seconds...")
    time.sleep(2)

print("Starting backend server in background...")
# Start server using the exact same command
cmd = ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
log = open('uvicorn_agent.log', 'w')
p = subprocess.Popen(cmd, stdout=log, stderr=log, cwd=r"D:\Graduation Project\backend\backend")
print(f"Started new uvicorn with PID {p.pid}")
