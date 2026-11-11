# 📋 وثيقة متطلبات المنتج (PRD)
## AI-COS — Artificial Intelligence Commerce Operating System
### صيدلية ذكية متعددة المستأجرين — الإصدار 1.0 (2026/2027)
**المالك:** محمد ياسر سعد نقودي (AI Engineer) · **الإشراف:** د/ سونة محمد حسن اسماعيل — كلية تكنولوجيا الإدارة ونظم المعلومات (BIS/MTIS) — جامعة بورسعيد

---

## 1. الرؤية (Vision)
تحويل الصيدلية من متجر أدوية تقليدي إلى **منظومة تشغيل ذاتية** يديرها وكلاء ذكاء اصطناعي: تفهم المريض (صوت وصورة ونص)، تتنبأ باحتياجاته الدوائية قبل نفادها، تحمي القرارات الحساسة بحوكمة رباعية العيون، وتحول كل قرار إلى أثر موثق غير قابل للتعديل.

## 2. المشكلة (Problem)
| مشكلة الصيدلية اليدوية | الأثر |
|---|---|
| صرف يدوي عرضة للخطأ (تشابه الأسماء LASA) | أخطار سريرية ومسؤولية قانونية |
| لا تتبع لدورات العلاج المزمنة | انقطاع علاج المرضى المزمنة وفقدان إيراد متكرر |
| قرارات شراء بالتخمين | رأس مال مجمّد في أصناف ميتة + نفاد الأصناف السريعة |
| لا مصدر لمعلومات السوق | الصيدلية آخر من يعرف بالسحبات والبدائل |
| سجلات قابلة للتعديل | لا مساءلة ولا امتثال |

## 3. المستخدمون (Personas)
| الشخصية | الدور | ما يحتاجه |
|---|---|---|
| صاحب/ة الصيدلية (Admin) | القرار والإشراف | لوحة KPIs حية · اعتمادMaker/Checker · راقب سوق |
| صيدلي/ة الصرف (Pharmacist) | الصرف والمراجعة | طابور HITL · فحص تداخلات · روشتات مقروءة |
| المريض/العميل (Storefront) | الشراء | بحث ومحادثة صوتية · رفع روشتة · أسعار موثقة · تذكير |
| محاسب (Accounting) | المالية | قيود يومية آلية · تقارير |

## 4. المتطلبات الوظيفية (Functional Requirements — المبنية فعليًا)
### 4.1 المتجر (Storefront)
- FR-1 كتالوج حي من قاعدة البيانات (138 دواء) ببحث وتصفية
- FR-2 سلة شراء + طلبات + كوبونات (CARE5/CARE15)
- FR-3 محادثة ذكية (RAG هجين: BM25 + BERT/pgvector 384ب) بمصادر موثقة
- FR-4 محادثة صوتية كاملة: 🎤 إدخال صوتي (Web Speech ar-EG) + 🔊 رد مسموع (Gemini Neural Leda + سلسلة احتياط)
- FR-5 رفع روشتة مكتوبة بخط اليد → TrOCR/Florence (خادم 9202) → مطابقة ≥65% + كارت أحمر لغير المتوفر

### 4.2 الوكلاء الـ 18 (Agentic Layer)
- FR-6 **Analytics**: Data analytics and business intelligence agent
- FR-7 **Automation**: Workflow automation agent
- FR-8 **Cross-Sell**: Recommends related products
- FR-9 **Customer Success**: Ensures customer satisfaction and retention
- FR-10 **Documentation**: Handles compliance and documentation
- FR-11 **Executive**: High-level executive agent for oversight
- FR-12 **Finance**: Handles financial reporting and operations
- FR-13 **Financial Vision**: Financial forecasting and planning
- FR-14 **Hybrid**: Hybrid search / operations
- FR-15 **Inventory**: Inventory management and alerts
- FR-16 **Market Intelligence**: Market analysis and intelligence
- FR-17 **Marketing**: Marketing campaigns and promotions
- FR-18 **Model Manager**: LLM model management and routing
- FR-19 **Orchestrator**: Orchestrates tasks among agents
- FR-20 **Pricing**: Dynamic pricing calculations
- FR-21 **Sales**: Sales processing and interactions
- FR-22 **Simulator**: Simulation and scenario testing
- FR-23 **Support**: Customer support agent

### 4.3 المحادثة (نموذج التوليد)
- FR-15 سلسلة متدرجة: Qwen 2.5 محلي → Gemma 31B سحابي → Gemini → رد سياقي — **بدون انقطاع**
- FR-16 منع الهلوسة: الإجابة من السياق المسترجع فقط + نفي صريح لغير المتوفر

### 4.4 الحوكمة (Governance)
- FR-17 Maker/Checker إلزامي للقرارات CRITICAL: هويتان مختلفتان (رفض نفس المستخدم) + تنفيذ مرة واحدة
- FR-18 WORM: سجل تدقيق بسلسلة SHA-256 + ربط خارجي عبر n8n worm-anchor
- FR-19 Outbox: كل حدث يمر بأعمدة payload_hash/worm_line_hash + retry → DEAD_LETTER
- FR-20 HITL: ما يخرج تلقائيًا دون مراجعة صيدلي عند ثقة 50-80%

### 4.5 الأمان
- FR-21 جلسات موقعة HMAC يملكها السيرفر (تجاهل تاريخ العميل الوارد)
- FR-22 تعقيم PII قبل أي مسار سحابي (اسم/هاتف/إيميل/رقم قومي)
- FR-23 SecurityGuard: صد حقن الأوامر + NFKC + أحرف تحكم مخفية + حد 60 req/min
- FR-24 عزل Multi-Tenant بـ RLS + fail-closed للمجهول

### 4.6 الميزات المضافة حديثاً
- **Function Calling**: الوكلاء يمكنهم استدعاء دوال مباشرة لتنفيذ العمليات.
- **CDSS-Triggered Actions**: نظام دعم القرار السريري يقوم بتوليد إجراءات آلية (actions) في حالة التعارضات الخطيرة.
- **Multi-Model Source Tracking**: تتبع مصدر النموذج المستخدم للشفافية وتوثيق الأداء لكل مسار.

## 5. المتطلبات غير الوظيفية (NFR — المقيسة فعليًا)
| النوع | المتطلب | المقيس |
|---|---|---|
| الدقة | صفر هلوسة في الفحوصات | 70/70 بنشمارك · 50/50 فيديو · **صفر تخمين** |
| الأمان | اختراق/تزييف/تقاطع مستأجرين | ✅ صد مؤكد حيًا (50/50) |
| الأداء | الحتمي <2.5ث · التوليد 4-17ث · TTS 2-13ث | ✅ مقيس |
| الموثوقية | تراجع ثلاثي + Outbox retry + cooldown | ✅ صفر انقطاع في ~120 نداء |
| التوفر | يعمل بلا إنترنت (محلي) وبيتدرج تلقائيًا | ✅ مختبر |

## 6. مؤشرات النجاح (KPIs — الأدلة الحية)
- بنشمارك 70/70 · فيديو 50/50 · kb_selfcheck 14/14
- سيناريو Maker/Checker: 4/4 (اعتماد · منع تكرار · WORM · Outbox SENT attempts=1)
- طوارئ القلب العامية: hard-stop 1.8-2.2 ثانية
- صفر هلوسة: رفض صريح لغير المتوفر (مثبت بسؤال التنسيق)

## 7. نطاق الإصدار 1.0 (Built) وما بعد
| مبني (v1.0) | بعد التخرج |
|---|---|
| كل ما سبق + 5 مفاتيح TTS (~50/يوم) | S3 Object Lock · تدريب Qwen على محادثات مصرية · مراقبة إنتاجية · تطبيقات عمودية (قهوة/أزياء جاهزة بالبنية) |

## 8. القيود (Constraints)
- GPU محلي (T1200) — التوليد المحلي أبطأ من السحابي (السلسلة تعالجها)
- حصة Gemini TTS المجانية (10/مفتاح/يوم → مسبح 5 مفاتيح = 50)
- الترخيص الطبي التجاري (قواعد DDI المرخصة) = قرار تشغيلي بعد التخرج
