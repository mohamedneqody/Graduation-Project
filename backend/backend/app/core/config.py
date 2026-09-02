from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    NEXT_PUBLIC_SUPABASE_URL: str
    NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: str
    SUPABASE_JWT_SECRET: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── LLM config (RAG Bot & Marketing) — 3-Tier Fallback ───────────────────
    # Priority 1: Gemini API (Cloud — الأسرع)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.7-flash"
    # Priority 2: AI-COS-Qwen-2.5 (Ollama محلي — احتياط بدون نت)
    OLLAMA_URL: str = "http://127.0.0.1:11434/api/generate"
    OLLAMA_MODEL: str = "AI-COS-Qwen-2.5"
    OLLAMA_TIMEOUT: float = 60.0
    # Priority 3: Context-only fallback (يعمل دائماً بدون LLM)
    # Priority 2b: DeepSeek عبر OpenRouter (احتياطي إضافي — اختياري)
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "deepseek/deepseek-r1-0528:free"
    OPENROUTER_URL: str = "https://openrouter.ai/api/v1/chat/completions"

    N8N_WEBHOOK_URL: str = ""
    DEFAULT_STOREFRONT_TENANT_ID: str = "62712616-be1e-4129-986f-4131877e63b8"
    SUPER_ADMIN_EMAIL: str = "mohameb.eslam460@gmail.com"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
