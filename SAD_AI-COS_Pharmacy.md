# Software Architecture Document (SAD)
## AI-COS — Pharmacy Vertical

| البيان | التفاصيل |
|---|---|
| **النوع** | مشروع تخرج جماعي — فريق من 8 أشخاص، بقيادة مهندس AI (Team Lead) |
| **مدة التنفيذ** | سنة أكاديمية كاملة |
| **الحالة** | معتمد بعد سلسلة قرارات معمارية مناقَشة ومبرَّرة |
| **يُكمّل** | AI-COS_Pharmacy_Use_Case.md، PRD_AI-COS_Pharmacy.md |

---

## 1. المبدأ المعماري العام

النظام **Modular Monolith واحد** (وليس Microservices)، مقسّم داخليًا لوحدات (Modules) بحدود واضحة تطابق تمامًا الـ Business Domains الموثقة في مستند AI-COS الأصلي (Phase 1). هذا القرار مقصود وليس تبسيطًا:

- **لفريق 8 أشخاص**: كل Domain = ملكية واضحة لعضو أو زوج من الفريق، بدون تضارب.
- **لسهولة العرض الحي**: تطبيق واحد يُشغَّل، لا شبكة من الخدمات المعقّدة وقت المناقشة.
- **لقابلية التطور لاحقًا**: أي Domain حدوده واضحة من اليوم الأول يسهل فصله كـ Microservice مستقبلًا (Evolutionary Architecture) دون إعادة بناء.

```
ai_cos_backend/  (تطبيق FastAPI واحد)
├── domains/
│   ├── identity_access/         → Team Member A
│   ├── multi_tenant/            → Team Member A
│   ├── commerce/                → Team Member B  (Store, Catalog, Orders, Payments)
│   ├── customer_engagement/     → Team Member C  (Behavioral Tracking, Notifications)
│   ├── data_ai/                 → Team Member D+E (Feature Store, ML Models, Decision Engine)
│   ├── ai_experience/           → Team Lead (AI Agents, RAG, Copilot)
│   ├── operations_visibility/   → Team Member F  (Workflow Automation, Analytics, Monitoring)
│   └── shared_kernel/           → مشترك (Auth helpers, Tenant context, Audit)
```

---

## 2. Tech Stack النهائي المعتمد

### 2.1 Frontend
| التقنية | الاستخدام |
|---|---|
| Next.js 15 (App Router) + React 19 | الإطار الأساسي |
| TypeScript | أمان الأنواع عبر الفريق |
| Tailwind CSS 4 + Shadcn/UI | نظام تصميم موحّد بين أعضاء الفريق |
| TanStack Query | إدارة حالة البيانات القادمة من API |
| React Hook Form + Zod | نماذج + تحقق من صحة البيانات |
| Zustand | إدارة الحالة المحلية الخفيفة |
| Apache ECharts | رسوم الـ Dashboard التحليلي |
| WebSockets / SSE | تحديث Dashboard لحظيًا (Monitoring & Observability) |

### 2.2 Backend
| التقنية | الاستخدام |
|---|---|
| FastAPI + Python 3.13 | Backend الأساسي |
| SQLAlchemy 2 (Async) + Alembic | ORM + إدارة الترحيلات (Migrations) |
| Pydantic v2 | التحقق من صحة البيانات والـ Schemas |
| AsyncPG + Uvicorn/Gunicorn | تشغيل غير متزامن + إنتاج |

### 2.3 Database & Storage
| التقنية | الاستخدام |
|---|---|
| Supabase (PostgreSQL) | قاعدة البيانات التشغيلية والتحليلية معًا (Schema منفصل للتحليلات) |
| Supabase Auth | تسجيل الدخول (Local + Google OAuth) + RLS لعزل الـ Tenants |
| pgvector (داخل Supabase) | Vector DB لطبقة RAG — بدون خدمة خارجية منفصلة |
| Redis | Cache، Session، AI Response Cache، Rate Limiting |

### 2.4 AI Layer
| التقنية | الاستخدام |
|---|---|
| **Gemma (محلي عبر Ollama)** | المهام البسيطة والسريعة (تصنيف، استخراج، ردود مباشرة) — يعمل على GPU 4GB |
| **مزوّد سحابي واحد (Claude/Gemini)** | المهام التي تحتاج تفكيرًا أعمق أو ردًا مباشرًا لعميل حقيقي |
| LlamaIndex | تنظيم طبقة RAG فوق pgvector |
| LangGraph | تنسيق الـ 14 AI Agent الموثقين في AI-COS (Orchestrator, Marketing, Sales, Support...) |
| MCP (Model Context Protocol) | ربط الـ Agents بأدوات خارجية (واتساب، إيميل، قاعدة البيانات) بشكل موحّد |
| PydanticAI / Instructor | إخراج منظَّم (Structured Output) من النماذج بدل تحليل نص حر |

### 2.5 Machine Learning
| التقنية | الاستخدام |
|---|---|
| Scikit-learn, XGBoost, LightGBM | نماذج Baseline والتنبؤ التقليدي |
| PyTorch | الشبكات العصبية (إن لزم) |
| SHAP | تفسير القرارات (Explainability) |
| MLflow | تتبّع تجارب النماذج المتعددة بين أعضاء فريق الـ AI |
| Pandas / Polars / DuckDB | معالجة وتحليل البيانات |

### 2.6 Automation & Messaging
| التقنية | الاستخدام |
|---|---|
| n8n (Self-hosted على Docker) | كل الـ Workflows: تذكير، Cross-sell، A/B Testing، KPI Aggregation |
| ~~RabbitMQ~~ | **مؤجَّل** — n8n + FastAPI Background Tasks كافيان لحجم MVP؛ يُضاف فقط لو ظهرت حاجة فعلية لاحقًا |

### 2.7 Monitoring & Observability (تنفيذ فعلي لـ Domain موثّق)
| التقنية | الاستخدام |
|---|---|
| Prometheus + Grafana | مقاييس النظام ولوحات مراقبة حية — تُظهر Domain "Monitoring & Observability" بشكل ملموس |
| Sentry | تتبّع الأخطاء (إعداد سريع، Free Tier كافٍ) |
| ~~OpenTelemetry + Loki~~ | **مؤجَّل** — مفيد أكتر في Microservices، أقل أولوية في Modular Monolith |

### 2.8 DevOps & Quality
| التقنية | الاستخدام |
|---|---|
| Docker + Docker Compose | تشغيل كل الخدمات محليًا كـ MVP |
| GitHub Actions | CI بسيط (اختبارات + Linting) — ضروري مع فريق 8 لتفادي تعارضات الكود |
| Pytest / Vitest | اختبارات Backend / Frontend |
| OpenAPI (تلقائي من FastAPI) + Mermaid | توثيق الـ API والمخططات |

### 2.9 قرارات مؤجَّلة/مرفوضة بوضوح (مع السبب)

| القرار | الحالة | السبب |
|---|---|---|
| RabbitMQ / Kafka | مؤجَّل | لا حاجة فعلية في حجم MVP الحالي |
| CQRS الكامل | جزئي فقط | يُطبَّق فقط على Analytics Dashboard إن لزم، وليس شاملًا |
| Feast Feature Store | مؤجَّل | جدول Postgres عادي كافٍ في هذه المرحلة |
| OpenTelemetry + Loki | مؤجَّل | تكلفة تعقيد أعلى من قيمته في Modular Monolith |
| Adapter لعدة LLM مدفوعة معًا (GPT-5.5+Claude+Gemini) | مرفوض | تكلفة مالية مستمرة بلا داعي؛ الاكتفاء بمزوّد سحابي واحد + Gemma محلي |

---

## 3. مصفوفة توزيع الفريق على الـ Domains

| Domain (من AI-COS الأصلي) | المسؤول المقترح | التقنيات الأساسية المستخدمة |
|---|---|---|
| Identity & Access, Multi-Tenant | عضو 1 | Supabase Auth, RLS |
| Store, Product Catalog, Orders, Payments | عضو 2 | FastAPI, SQLAlchemy |
| Behavioral Tracking, Notifications | عضو 3 | Session/Event Tables, n8n |
| Feature Store, Data Engineering | عضو 4 | Pandas, DuckDB, Postgres |
| Machine Learning Models, Continuous Learning | عضو 5 | Scikit-learn, XGBoost, MLflow, SHAP |
| AI Agents, Knowledge/RAG, Executive Copilot | Team Lead (مهندس AI) | LangGraph, MCP, LlamaIndex, Gemma |
| Workflow Automation, Analytics, Monitoring | عضو 6 | n8n, Prometheus, Grafana |
| Frontend (متجر + Dashboard) | عضو 7 + عضو 8 | Next.js, React, ECharts |

> ملاحظة: التوزيع مرن وقابل للتعديل حسب مهارات الفريق الفعلية، لكن المبدأ الثابت هو: **كل Domain له مسؤول واضح واحد على الأقل**، لمنع التداخل والتعارض في الكود.

---

## 4. طبقة تنسيق الـ AI Agents (LangGraph + MCP)

بما أن مستند AI-COS الأصلي وثّق 14 دورًا آليًا بالاسم (Manager/Orchestrator Agent، Marketing Agent، Sales Agent، Inventory Agent، Pricing Agent، Customer Success Agent، Finance Agent، Support Agent، Automation Agent، Documentation Agent، Analytics Agent، Executive Copilot، AI Decision Engine، AI Website Controller)، فإن **LangGraph هو الأداة المصمَّمة تحديدًا لهذا النمط**: تنسيق عدة Agents متخصصة تحت مايسترو واحد (Orchestrator).

```
                    ┌─────────────────────────┐
                    │   Orchestrator Agent      │
                    │   (LangGraph Graph Root)   │
                    └────────────┬────────────┘
                                 │
        ┌──────────────┬────────┼────────┬──────────────┐
        ▼              ▼        ▼        ▼              ▼
  Marketing Agent  Sales Agent  ...  Support Agent  Executive Copilot
        │                                  │
        ▼                                  ▼
   [MCP: n8n Tool]                  [MCP: Knowledge/RAG Tool]
```

**MCP** هنا هو الطبقة الموحّدة التي تسمح لأي Agent بالوصول لأدوات خارجية (إرسال واتساب عبر n8n، الاستعلام عن قاعدة المعرفة عبر RAG، قراءة/كتابة في قاعدة البيانات) دون كتابة تكامل مخصص لكل أداة على حدة — وهذا يقلل تكرار الكود بشكل كبير مع فريق يبني عدة Agents بالتوازي.

---

## 5. استراتيجية النشر (Deployment Strategy)

| المرحلة | البيئة |
|---|---|
| **MVP الحالي** | Docker Compose محليًا على جهاز الفريق (FastAPI, n8n, Redis, Prometheus/Grafana, Ollama) + Supabase Cloud (مجاني) |
| **قبل العرض النهائي** | يُقيَّم الانتقال لاستضافة سحابية بسيطة (مثل Render/Railway للـ Backend + Vercel للـ Frontend) إذا احتاج العرض وصولًا خارجيًا للجنة |

---

## 6. الخطوة التالية

بعد اعتماد هذا الـ SAD، الخطوات الموازية المقترحة:
1. **بدء توليد/تجهيز Synthetic Data** متوافقة مع ERD المعتمد (لا يوجد سبب للانتظار بعد استقرار الـ Schema).
2. **إعداد Docker Compose الأساسي** (FastAPI + Supabase local + Redis + n8n + Ollama) كأول Sprint للفريق.
3. **توزيع الـ Domains فعليًا على الأعضاء** بناءً على مصفوفة القسم 3، بعد تعديلها حسب مهارات كل عضو الحقيقية.
