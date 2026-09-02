import sys
import traceback

def check():
    try:
        from app.main import app
        print("Backend imported successfully. No syntax or basic import errors.")
    except Exception as e:
        print("Error importing app:")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    check()
