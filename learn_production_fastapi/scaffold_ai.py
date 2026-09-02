import os
import re

base_path = r"d:\Graduation Project\learn_production_fastapi"

files = {
    "app/routers/ai.py": '''"""
# مسؤوليته:
# إدارة نقاط النهاية (Endpoints) الخاصة بالذكاء الاصطناعي (AI).
# يشمل الدردشة العادية، تضمين النصوص (Embeddings)، قواعد البيانات المتجهة (Vector DB)،
# ودمجها معاً في تطبيق RAG (Retrieval-Augmented Generation)، وتنسيق الـ Multi-Agent.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services import ai as ai_service

router = APIRouter(prefix="/api/v1/ai", tags=["AI Integration"])

class ChatRequest(BaseModel):
    message: str

class DocumentRequest(BaseModel):
    text: str

class SearchRequest(BaseModel):
    query: str

class MultiAgentRequest(BaseModel):
    topic: str

# 1. Chat Endpoint
@router.post("/chat")
async def chat_with_ai(request: ChatRequest):
    """
    يتصل بـ API خارجي (مثال: Gemini) ويرجع الرد.
    مفتاح الـ API مخفي في ملف .env (كـ GEMINI_API_KEY).
    """
    response_text = await ai_service.call_gemini_api(request.message)
    return {"reply": response_text}

# 2. Local Embeddings Endpoint
@router.post("/embeddings")
async def generate_embedding(request: DocumentRequest):
    """
    يحول النص إلى متجه (Vector) باستخدام نموذج محلي (Sentence-Transformers).
    نرجع طول المتجه فقط للتحقق من العمل.
    """
    vector = ai_service.get_local_embedding(request.text)
    return {"vector_length": len(vector), "sample_first_3": vector[:3]}

# 3. ChromaDB Endpoints (Vector DB)
@router.post("/knowledge/add")
async def add_knowledge(request: DocumentRequest):
    """يضيف النص إلى قاعدة المعرفة المتجهة المحلية."""
    doc_id = ai_service.add_to_chroma(request.text)
    return {"message": "Knowledge added successfully", "doc_id": doc_id}

@router.post("/knowledge/search")
async def search_knowledge(request: SearchRequest):
    """يبحث في قاعدة المعرفة عن أقرب نص مشابه للسؤال."""
    results = ai_service.search_chroma(request.query)
    return {"results": results}

# 4. RAG Endpoint (Retrieval-Augmented Generation)
@router.post("/rag")
async def rag_chat(request: ChatRequest):
    """
    يدمج البحث في ChromaDB مع Gemini API للإجابة من سياق محدد.
    """
    # الخطوة 1: استرجاع المعلومات المتعلقة من الـ Vector DB
    relevant_docs = ai_service.search_chroma(request.message)
    context = " ".join(relevant_docs) if relevant_docs else "لا توجد معلومات إضافية."
    
    # الخطوة 2: صياغة الـ Prompt المدمج
    augmented_prompt = f"""أجب على السؤال بناءً على السياق التالي فقط. 
السياق: {context}
السؤال: {request.message}"""
    
    # الخطوة 3: إرسال الـ Prompt للـ AI
    response_text = await ai_service.call_gemini_api(augmented_prompt)
    return {"reply": response_text, "context_used": context}

# 5. Multi-Agent Endpoint
@router.post("/multi-agent")
async def run_multi_agent(request: MultiAgentRequest):
    """
    ينسق العمل بين وكيلين (Agents) منفصلين لتنفيذ مهمة مركبة.
    """
    # العميل الأول (الباحث)
    raw_data = await ai_service.agent_researcher(request.topic)
    
    # العميل الثاني (الكاتب) يعتمد على مخرجات الأول
    final_article = await ai_service.agent_writer(raw_data)
    
    return {
        "topic": request.topic,
        "research_data": raw_data,
        "final_article": final_article
    }
''',

    "app/services/ai.py": '''"""
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
    prompt = f"أنت كاتب محترف. خذ هذه الحقائق الجافة واصنع منها فقرة واحدة جذابة ومترابطة:\\n{research_data}"
    return await call_gemini_api(prompt)
'''
}

for rel_path, content in files.items():
    full_path = os.path.join(base_path, rel_path.replace("/", os.sep))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

# تسجيل الـ Router في main.py
main_py_path = os.path.join(base_path, "app/main.py")
with open(main_py_path, "r", encoding="utf-8") as f:
    main_content = f.read()

if "from app.routers import products, demo_async, files, tasks, ai" not in main_content:
    main_content = main_content.replace(
        "from app.routers import products, demo_async, files, tasks",
        "from app.routers import products, demo_async, files, tasks, ai"
    )
    if "app.include_router(ai.router)" not in main_content:
        main_content += "\napp.include_router(ai.router)\n"
    
    with open(main_py_path, "w", encoding="utf-8") as f:
        f.write(main_content)

print("AI endpoints configured.")
