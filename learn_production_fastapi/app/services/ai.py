"""
# مسؤوليته:
# التواصل مع النماذج الخارجية (APIs) والمحلية (Local Models).
# وإدارة قاعدة البيانات المتجهة (ChromaDB) والتنسيق بين وكلاء الـ Multi-Agent.
"""
import os
import uuid
import httpx
try:
    from sentence_transformers import SentenceTransformer
    import chromadb
except ImportError:
    SentenceTransformer = None
    chromadb = None

from app.core.config import settings

# تهيئة النماذج المحلية في الذاكرة (تُحمّل مرة واحدة عند تشغيل التطبيق)
# تم وضع try-except لأن هذه المكتبات ثقيلة وقد لا تكون مثبتة على بيئة المستخدم على الفور.
model = None
chroma_client = None
collection = None

if SentenceTransformer and chromadb:
    # 1. نموذج التضمين المحلي
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # 2. إعداد ChromaDB محلي (In-Memory للتجربة السريعة)
    chroma_client = chromadb.Client()
    collection = chroma_client.create_collection(name="knowledge_base")

async def call_gemini_api(prompt: str) -> str:
    """يتصل بـ Gemini API مجاني (يحتاج لـ GEMINI_API_KEY في .env)."""
    api_key = os.getenv("GEMINI_API_KEY", "dummy_key")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            # محاكاة في حالة عدم وجود API Key صحيح لتجنب توقف التطبيق التعليمي
            return f"[Fake Response for demo] AI says: I received '{prompt}'. (Error: {str(e)})"

def get_local_embedding(text: str) -> list[float]:
    """ينشئ الـ Embedding باستخدام النموذج المحلي."""
    if not model:
        # محاكاة في حال لم يتم تثبيت المكتبات الثقيلة
        return [0.1, 0.2, 0.3] * 128
    
    # تحويل النص لـ Vector وتحويله لـ list ليتمكن FastAPI من إرجاعه كـ JSON
    vector = model.encode(text)
    return vector.tolist()

def add_to_chroma(text: str) -> str:
    """يضيف النص ومتجهه إلى ChromaDB."""
    if not collection:
        return str(uuid.uuid4())
        
    doc_id = str(uuid.uuid4())
    embedding = get_local_embedding(text)
    
    collection.add(
        documents=[text],
        embeddings=[embedding],
        ids=[doc_id]
    )
    return doc_id

def search_chroma(query: str, n_results: int = 1) -> list[str]:
    """يبحث عن النصوص المشابهة في ChromaDB."""
    if not collection:
        return ["هذه نتيجة وهمية لأن ChromaDB غير مثبت."]
        
    query_embedding = get_local_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )
    
    if results and "documents" in results and results["documents"]:
        return results["documents"][0]
    return []

# --- Multi-Agent Setup ---

async def agent_researcher(topic: str) -> str:
    """
    العميل 1: الباحث. 
    وظيفته تجميع الحقائق والنقاط الأساسية حول الموضوع فقط.
    """
    prompt = f"أنت باحث خبير. أعطني 3 حقائق سريعة ومختصرة عن: {topic}"
    return await call_gemini_api(prompt)

async def agent_writer(research_data: str) -> str:
    """
    العميل 2: الكاتب. 
    وظيفته أخذ الحقائق الجافة وصياغتها في فقرة أدبية جذابة.
    """
    prompt = f"أنت كاتب محترف. خذ هذه الحقائق الجافة واصنع منها فقرة واحدة جذابة ومترابطة:\n{research_data}"
    return await call_gemini_api(prompt)
