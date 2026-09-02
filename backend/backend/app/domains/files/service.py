from fastapi import UploadFile
import shutil
import os
import time

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def process_file_in_background(filename: str):
    """Simulates a background task like OCR or image resizing."""
    time.sleep(2)
    print(f"Background task completed for {filename}")

async def handle_file_upload(file: UploadFile):
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
        
    # Get file size
    size = os.path.getsize(file_location)
    
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": size,
        "message": "File uploaded successfully"
    }
