from pydantic import BaseModel
from typing import Optional

class AIChatRequest(BaseModel):
    message: str

class AIChatResponse(BaseModel):
    reply: str
    llm_source: Optional[str] = None    # gemini:gemini-2.5-flash | ollama:gemma3:4b | context_only
    response_time_ms: Optional[int] = None
