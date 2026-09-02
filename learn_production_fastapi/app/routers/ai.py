"""
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
