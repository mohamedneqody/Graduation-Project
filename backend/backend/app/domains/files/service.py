from fastapi import UploadFile
import os
import time
import uuid
import hashlib
from pathlib import Path

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def process_file_in_background(filename: str):
    """Simulates a background task like OCR or image resizing."""
    time.sleep(2)
    print(f"Background task completed for {filename}")

async def handle_file_upload(file: UploadFile):
    # Never use a client supplied filename as a storage path.  A UUID prevents
    # traversal/collision bugs and binds one uploaded object to one record.
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".pdf"}:
        raise ValueError("Unsupported prescription file type")

    stored_filename = f"{uuid.uuid4().hex}{suffix}"
    file_location = os.path.join(UPLOAD_DIR, stored_filename)
    hasher = hashlib.sha256()
    size = 0
    max_size = 15 * 1024 * 1024
    try:
        with open(file_location, "xb") as file_object:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > max_size:
                    raise ValueError("Prescription file exceeds 15 MB limit")
                hasher.update(chunk)
                file_object.write(chunk)
    except Exception:
        if os.path.exists(file_location):
            os.remove(file_location)
        raise
    
    return {
        "filename": stored_filename,
        "content_type": file.content_type,
        "size": size,
        "sha256": hasher.hexdigest(),
        "message": "File uploaded successfully"
    }
