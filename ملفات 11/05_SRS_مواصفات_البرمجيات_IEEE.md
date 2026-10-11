# 📄 وثيقة مواصفات البرمجيات (SRS) — وفق IEEE 830 المُكيَّف
## AI-COS Pharmacy — الإصدار 1.0 · 2026/2027
*(هذه الوثيقة تُشتق من PRD وتُكمّلها بتفاصيل الواجهات والسلوك الدقيق — الأرقام المقيسة مُثبتة في تقرير الاختبارات المرفق)*

---

## 1. Introduction
### 1.1 Purpose
تحديد المتطلبات الوظيفية وغير الوظيفية لنظام AI-COS: منظومة صيدلية ذكية متعددة المستأجرين تجمع الـ Agentic AI (9 وكلاء) مع RAG هجين ومعالجة رؤية للروشتات وحوكمة تدقيق غير قابلة للتعديل.
### 1.2 Scope
النطاق المبنى (v1.0): متجر + محادثة RAG صوتية + 9 وكلاء + قراءة روشتات + حوكمة Maker/Checker + WORM + Outbox + تعدد مستأجرين (صيدلية/قهوة/أزياء). خارج النطاق (v2): بوابات دفع متعددة، تطبيقات جوال أصلية، S3 Object Lock.
### 1.3 Definitions
RAG · pgvector · BM25 · HITL · Maker/Checker · WORM · Outbox Pattern · DEAD_LETTER · LASA · RFM/CLV · SHAP · DDI

## 2. Overall Description
- **معمارية:** FastAPI (174+ endpoint) + Next.js 16 + PostgreSQL/Supabase (RLS) + Redis/Celery + n8n (أتمتة) + خادم رؤية مستقل (9202)
- **التوليد:** سلسلة متدرجة Qwen 2.5 محلي → Gemma 31B → Gemini → رد سياقي
- **الاسترجاع:** Hybrid — BM25 + BERT MiniLM 384ب في pgvector
- **الحوكمة:** Maker/Checker إلزامي للـ CRITICAL + WORM SHA-256 + Outbox
- **قيود:** GPU محلي (T1200) · حصص سحابية مجانية (تدوير 5 مفاتيح TTS)

## 3. Specific Requirements
### 3.1 Functional (مختصرة — التفصيل في PRD §4 والـ Traceability Matrix)
| ID | المتطلب | الأولوية | الحالة |
|---|---|---|---|
| FR-1..5 | متجر + محادثة RAG + صوت ثنائي الاتجاه + روشتات | Must | ✅ مبني ومختبر |
| FR-6..14 | 9 وكلاء (سوق/تسعير/مخزون/تسويق/بيع/مالية/نجمة عملاء/دعم/أتمتة) | Must | ✅ مختبر حيًا 9/9 |
| FR-15/16 | سلسلة توليد متدرجة + منع هلوسة | Must | ✅ مختبر (رفض صريح لغير المتوفر) |
| FR-17..20 | Maker/Checker + WORM + Outbox + HITL | Must | ✅ سيناريو حي 4/4 |
| FR-21..24 | الأمان (جلسات/تعقيم/عزل/حد طلبات) | Must | ✅ مختبر حيًا |
### 3.2 Non-Functional (المقيس)
| ID | المتطلب | القيمة المقيسة |
|---|---|---|
| NFR-الدقة | صفر هلوسة | 70/70 بنشمارك · رفض صريح موثق |
| NFR-الأمان | صد الحقن والتزييف | 50/50 · حظر حي موثق |
| NFR-الأداء | الحتمي ≤2.5s · التوليد ≤17s محلي | ✅ مقيس |
| NFR-الموثوقية | صفر انقطاع عبر السلسلة | ✅ ~120 نداء متتالي |
| NFR-الاستعادة | Outbox retry→DEAD_LETTER | ✅ SENT attempts=1 موثق |

## 4. External Interfaces
| الواجهة | البروتوكول | الاتجاه |
|---|---|---|
| المتصفح → Next.js | HTTPS | المستخدم |
| Next.js → FastAPI | REST /api/v1 (+SSE للبث) | المطور |
| FastAPI → Supabase | asyncpg/Pooler 5432 + RLS | الخادم |
| FastAPI → Ollama | localhost:11434 (Qwen/Gemma) | الداخلي |
| FastAPI → Gemini | REST (LLM احتياط + TTS عصبي + استخبارات) | السحابي |
| خادم الرؤية | TrOCR/Florence :9202 | الداخلي |
| n8n → Webhooks | REST + Internal Token | الأتمتة |

## 5. Non-Functional Details
الأداء المقيس لكل مسار موثق في `06_تقرير_الاختبارات` · التوفر عبر السلسلة المتدرجة (صفر انقطاع) · الاستعادة عبر Celery retry + Outbox · الأمان تفصيله في PRD §4.5 + أدلة الحوكمة المرفقة.

## 6. Traceability
كل FR مربوط بـ: (أ) كود مصدره (ب) اختبار يغطيه (ج) دليل تشغيلي — في `مصفوفة التتبع` داخل وثيقة تحليل النظام (03).
