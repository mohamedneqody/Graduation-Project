import os

base_path = r"d:\Graduation Project\backend\backend\app\domains\files"

files = {
    "__init__.py": "",
    "schemas.py": '''from pydantic import BaseModel

class FileUploadOut(BaseModel):
    filename: str
    content_type: str
    size: int
    message: str
''',
    "service.py": '''from fastapi import UploadFile
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
''',
    "router.py": '''from fastapi import APIRouter, UploadFile, File, BackgroundTasks, status
from . import schemas, service

router = APIRouter()

@router.post("/upload", response_model=schemas.FileUploadOut, status_code=status.HTTP_201_CREATED)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Endpoint for uploading a file (Image/PDF).
    It saves the file and triggers a background task for processing (e.g., OCR).
    """
    result = await service.handle_file_upload(file)
    
    # Trigger background task
    background_tasks.add_task(service.process_file_in_background, file.filename)
    
    return result
'''
}

for name, content in files.items():
    with open(os.path.join(base_path, name), "w", encoding="utf-8") as f:
        f.write(content)
