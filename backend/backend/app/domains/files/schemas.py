from pydantic import BaseModel

class FileUploadOut(BaseModel):
    filename: str
    content_type: str
    size: int
    message: str
