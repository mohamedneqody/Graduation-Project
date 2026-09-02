import sys
sys.path.append(r"D:\Graduation Project\backend\backend")
from app.worker import cleanup_prescription_retention_task

if __name__ == "__main__":
    print("Running cleanup_prescription_retention_task...")
    result = cleanup_prescription_retention_task()
    print("Result:", result)
