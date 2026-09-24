# 🛡️ تقرير التدقيق المعمّق والتحقق الصارم الشامل (AI-COS Pharmacy)
**تاريخ الفحص والتحقق المستقل:** 14 سبتمبر 2026  
**طبيعة المهمة:** فحص كود بكود، ملف بملف، وسطر بسطر للواجهتين الأمامية والخلفية، ومراجعة نقدية دقيقة لفحص المدقق السابق وتصحيح انحرافاته مع إثبات الأدلة الحية بالكامل (اكتشاف وتوثيق قطعي دون تعديل أي ملف مصدري).

---

## 📑 فهرس محتويات التقرير
1. **المراجعة النقدية وتفنيد تقرير الفاحص السابق (Prior Attempt Debunking & Corrections)**
2. **التحقق من الإصلاحات السابقة وسجل التعديلات (Git History & Claimed Fixes)**
3. **فحص الواجهة الأمامية صفحة بصفحة (Frontend Comprehensive Audit - 26 Routes)**
4. **فحص نقاط النهاية الخلفية (Backend Comprehensive Audit - 150 Operations)**
5. **فحص الثغرات الأمنية الشائعة (Security Vulnerabilities & Auth Providers)**
6. **الاتساق مع القواعد الثابتة والصور (Hardcoding & Placeholder Consistency)**
7. **القائمة الموحدة للمشكلات والثغرات مرتبة حسب الخطورة (Critical → Cosmetic)**
8. **الأسئلة المعلقة والفجوات (Remaining Questions & Gaps)**

---

## 1. المراجعة النقدية وتفنيد تقرير الفاحص السابق (Challenging & Correcting Prior Findings)

قام الفاحص المستقل بمراجعة ادعاءات التقرير السابق واختبارها عملياً على البيئة الحقيقية، وتبيّن وجود **أخطاء جسيمة، وتلفيق لبيانات فحص الحزم، وتفسيرات غير صحيحة لأسباب انهيار الاختبارات**:

| الموضوع | ادعاء الفاحص السابق | ما أثبته الفحص الفعلي للكود والتشغيل الحي | التصحيح والنتيجة الدقيقة |
| :--- | :--- | :--- | :--- |
| **ثغرات الباك إند (`pip-audit`)** | ادّعى وجود **46 ثغرة فقط** في 3 حزم (`transformers 4.44.2` بها 44 ثغرة، `accelerate` ثغرة، `ecdsa` ثغرة). | تشغيل `python -m pip_audit` الفعلي أنتج **183 ثغرة معروفة في 26 حزمة برمجية**! حزمة `transformers` و `ecdsa` غير موجودتين إطلاقاً في التقرير! | **تصحيح جوهري:** الفاحص السابق نسَخ أو اختلق أرقاماً غير حقيقية؛ الثغرات الفعلية تشمل `aiohttp 3.13.3` (48 ثغرة تشمل RCE و DoS)، `gitpython 3.1.50` (26 ثغرة RCE)، `pillow` (25 ثغرة)، و `starlette 0.38.6` (14 ثغرة بنواة FastAPI نفسها)! |
| **ثغرات الفرونت إند (`npm audit`)** | ذكر ثغرة واحدة حرجة فقط في Next.js (RCE على Windows). | تشغيل `npm audit` أظهر **3 ثغرات (1 حرجة + 2 عالية)**: إحداها في `js-yaml` (DoS) والأخرى في `sharp` (libheif vulnerabilities). | **تصحيح وإكمال:** إغفال ثغرتي `js-yaml` و `sharp`. |
| **فشل اختبارات التوافقية (Starlette Routing)** | صنّفه كثغرة **حرجة (CRITICAL)** زاعماً فشل اختبارين في `test_agent_governance_hardening.py:207` و `test_quality_guards.py:91`. | تشغيل `pytest tests/test_agent_governance_hardening.py tests/test_quality_guards.py` نجح بنسبة **100% (20 passed, 0 failed)** في 12.22 ثانية. | **تفنيد قاطع:** الاختبارات تعمل وتنجح بالكامل في بيئة بايثون 3.12 الخاصة بالمشروع؛ وتصنيف خطأ في دالة اختبار (Test assertion) كثغرة حرجة كان تضخيماً غير مهني. |
| **أخطاء الاختبارات الـ 8 (Pytest Errors)** | زعم أن 8 اختبارات فشلت بسبب `ConnectionRefusedError: [WinError 10061]` عند الاتصال بـ Docker PostgreSQL (`55432`). | التتبع الفعلي للأخطاء (Traceback) أظهر أن السبب هو: `AttributeError: 'FixtureDef' object has no attribute 'unittest'` في `pytest_asyncio/plugin.py:321`. | **تصحيح السبب الجذري:** السبب هو عدم توافق برمجي بين `pytest 8.2.0` ومكتبة `pytest-asyncio 0.23.5` عند تهيئة فيكستشر `async_client`، وليس إغلاق حاوية Docker إطلاقاً! |
| **معرفات عملاء OAuth في Supabase** | زعم أن Google Client ID هو `593740882195-...` وأن Facebook ID هو `172944...`. | الفحص الميداني المباشر لترويسات الاستجابة `HTTP 302` أظهر: Google Client ID هو `488693887530-4cde34g0rtivcufc2eua0hass05n2j4r.apps.googleusercontent.com`، و Facebook Client ID هو `1331158659173302`. | **تصحيح أدلة الإثبات:** المعرفات المسجلة تعمل وتوجه بنجاح، لكن الفاحص السابق أورد أرقاماً عشوائية/قديمة. |
| **فحص الأزرار والواجهة (Dead Buttons)** | ادّعى فحص كل زر وصفحة ولم يرصد أي زر ميت أو نموذج مضلل. | التدقيق البرمجي المباشر لكود المكونات كشف عن **زر معاينة ميت تماماً** في صفحة الطلبات `admin/orders/page.tsx:328`، و **5 أخطاء ESLint** و 27 تحذيراً لـ React 19 Strict Hooks. | **اكتشاف جديد:** توثيق الأزرار المهملة بصرياً وأخطاء رندر المكونات داخل الصفحات. |

---

## 2. التحقق من الإصلاحات السابقة وسجل التعديلات (Git History & Claimed Fixes)

### أ. فحص آخر التعديلات عبر Git History (`git log --oneline -30`)
تم استعراض آخر 30 تعديلاً في مستودع `AI-COS-Pharmacy`:
```text
a1b75c9 feat(ops): professional launcher with ghost-process cleanup and real health checks
1c008e5 fix(accounting): verdicts derived from actual ledger state + kit alignment
5e67704 fix(architecture): honest UAT rendering + computed feasibility ROI + kit header
a9a3c90 fix(governance): risk-register summary computed from risks + kit alignment
7a2df31 feat(ui): orders page — status-colored rows, semantic filter pills, badge dots
582286f feat(ui): customer directory header identity, tier legend, and micro-interactions
b202fc0 feat(ui): admin dashboard card animation and per-module color identity
4d30de1 feat(ui): auto-verify hash chain on audit trail page load
8cfb78a fix(ui): audit hero gradient as inline style — immune to stale CSS cache
e511aa1 feat(ui): audit trail hero header — royal gradient banner and glow-on-verify chain strip
f855b99 feat(ui): audit trail coloring + dedicated hash-chain status strip + server-side category filter
1b5d620 chore: remove one-off patch scripts — scratch automation, not project code
e4da90b feat(ui): business-value dashboard readability, loading states, and honest A/B verdicts
f1c7333 feat(governance): declare live CDSS thresholds + LLM sequences in admin settings (read-only)
f2f5bc0 feat: operational guards hardening, config-driven thresholds, and admin UX polish
b4cd1d4 feat(ui): implement tabbed segmented navigation in AnalyticsEnterpriseCard
23a959c feat(analytics): elevate Analytics Agent to BIS 10/10 standard with AOV, Monthly Revenue at Risk
a1bf677 fix(agents): resolve undefined tenant_id on events table and wrap analytics queries
75a8e3a feat(analytics): overhaul Analytics Agent with real DB aggregations
3652074 تحديث شامل: إصلاحات أمنية + تصميم + إحصائيات
```

### ب. التحقق العملي من الإصلاحات السابقة المذكورة في المستندات
1. **منع استيلاء الحسابات (Account Takeover - ATO):**
   - **المسار:** [`backend/app/domains/auth/router.py:59-62`](file:///d:/Graduation%20Project/AI-COS-Pharmacy/backend/app/domains/auth/router.py#L59-L62)
   - **التحقق:** الكود يوضح صراحة:
     ```python
     # 2. Email auto-linking REMOVED (account-takeover vector).
     # New signups always get a fresh, independent Customer profile.
     ```
     تم التأكد برمجياً من إلغاء الدمج التلقائي بالحسابات القديمة بمجرد تطابق الإيميل.
2. **منع انتحال المستأجر بواسطة العميل (Client Tenant Spoofing):**
   - **المسار:** [`backend/app/domains/auth/router.py:68`](file:///d:/Graduation%20Project/AI-COS-Pharmacy/backend/app/domains/auth/router.py#L68)
   - **التحقق:** الكود يفرض: `target_tenant_id = None # Client cannot control tenant_id`، ويتم استخلاصه حصرياً من السيرفر.
3. **حماية CORS ورفض النطاقات الأجنبية:**
   - **التحقق الحي:** تم إرسال طلب OPTIONS مشبوه:
     ```bash
     curl.exe -s -I -H "Origin: https://evil-attacker.com" -H "Access-Control-Request-Method: POST" -X OPTIONS http://127.0.0.1:8000/api/v1/governance/approve
     ```
     رد السيرفر فوراً برفض قاطع: `HTTP/1.1 400 Bad Request` مع `Disallowed CORS origin`.
4. **محدد الطلبات الحي (SlowAPI Rate Limiter):**
   - **التحقق الحي:** أرسلنا 7 طلبات متتابعة وفورية إلى مسار الاتصال المحدود بـ `5/minute` في [`customer/router.py:100`](file:///d:/Graduation%20Project/AI-COS-Pharmacy/backend/app/domains/customer/router.py#L100):
     ```text
     النتيجة الفعلية عبر بايثون: [200, 200, 200, 200, 200, 429, 429]
     ```
     أول 5 طلبات نجحت (200)، وانطلق الحظر التلقائي فوراً في الطلبين السادس والسابع برموز `HTTP 429 Too Many Requests`.
5. **سلسلة التدقيق وحوكمة القرارات (WORM Ledger):**
   - **المسار:** [`backend/app/domains/agents/documentation.py`](file:///d:/Graduation%20Project/AI-COS-Pharmacy/backend/app/domains/agents/documentation.py) و `worm_ledger.py`.
   - **التحقق:** كل قيد يتم حسابه بـ SHA-256 مع ربطه بالهاش السابق (`prev_hash`) ودمجه في جدول التدقيق وسجل JSONL الخارجي.

---

## 3. فحص الواجهة الأمامية صفحة بصفحة (Frontend Audit — All 26 Routes)

تم حصر جميع ملفات `page.tsx` الـ 26 الموجودة فعلياً في `src/app`، واختبار كل صفحة عبر طلب HTTP مباشر للتأكد من عدم وجود أخطاء 500 أو 404، مع فحص النماذج والأزرار:

| # | المسار (Route) | الملف الفعلي في `src/app` | استجابة HTTP | النماذج والأزرار وحالة الربط بالـ API |
|:---:|:---|:---|:---:|:---|
| 1 | `/login` | `(auth)/login/page.tsx` | **200 OK** | نماذج تسجيل الدخول، إنشاء الحساب، استعادة كلمة المرور، وأزرار OAuth (Google/GitHub/Facebook). جميعها متصلة بـ Supabase Client Auth. |
| 2 | `/` | `(storefront)/page.tsx` | **200 OK** | نافذة رفع الروشتة الذكية (متصلة بـ `/api/v1/prescriptions/upload`)، شريط البحث، والتنقل. |
| 3 | `/about` | `(storefront)/about/page.tsx` | **200 OK** | صفحة تعريفية أكاديمية بمواصفات BIS ومصفوفات الأمان السريري. لا توجد نماذج ميتة؛ روابط الكتالوج والتواصل فعالة. |
| 4 | `/catalog` | `(storefront)/catalog/page.tsx` | **200 OK** | تصفية الفئات، البحث الحي، أزرار "أضف للسلة" و"تفاصيل الدواء" متصلة بنقاط النهاية الحية. |
| 5 | `/contact` | `(storefront)/contact/page.tsx` | **200 OK** | نموذج اتصال حقيقي يرسل لـ `POST /api/v1/customers/contact` ومحمى بـ Rate limit (5/min). |
| 6 | `/profile` | `(storefront)/profile/page.tsx` | **200 OK** | **تنبيه حرج:** زر "إعادة التعبئة السريعة" (Quick Refill) يرسل معرفاً نصياً معطوباً (`refill-${slug}`) بدلاً من UUID مما يعطل الشراء لاحقاً في السلة! زر "تجهيل الحساب" متصل ويعمل. |
| 7 | `/checkout` | `checkout/page.tsx` | **200 OK** | نموذج تأكيد الطلب وتطبيق الكوبونات متصل بـ `POST /api/v1/orders/` و `validate-coupon`. يفشل بـ 422 إذا احتوت السلة على عناصر من Quick Refill. |
| 8 | `/orders` | `orders/page.tsx` | **200 OK** | جدول استعراض طلبات المريض وحالات الشحن والـ ETA متصل بـ `GET /api/v1/orders/`. |
| 9 | `/admin` | `admin/page.tsx` | **200 OK** | بطاقات المؤشرات الرئيسية (KPIs) وروابط اللوحات التسع متصلة ومفعّلة. |
| 10 | `/admin/accounting` | `admin/accounting/page.tsx` | **200 OK** | ميزان المراجعة ودفتر اليومية المزدوج، زر المزامنة متصل بـ `/api/v1/accounting/ledger`. |
| 11 | `/admin/agentic-ai` | `admin/agentic-ai/page.tsx` | **200 OK** | 4 لوحات لوكلاء الذكاء الاصطناعي التسعة (Supervisor, Pricing, Marketing, Finance, etc.). جميع أزرار التوليد والتنفيذ متصلة بـ `/api/v1/agents/*`. |
| 12 | `/admin/ai-review` | `admin/ai-review/page.tsx` | **200 OK** | طابور مراجعة الروشتات للصيدلي، متصل بـ `/api/v1/prescriptions/`. |
| 13 | `/admin/analytics` | `admin/analytics/page.tsx` | **200 OK** | تحليلات AOV، الإيرادات المعرضة للخطر، ومعدل التسرب، متصلة بنقطة التحليلات وتجميعات SQL. |
| 14 | `/admin/audit-logs` | `admin/audit-logs/page.tsx` | **200 OK** | سجل التدقيق وسلسلة الهاشات WORM، زر التصدير CSV والتحقق متصل بـ `/governance/audit-logs`. |
| 15 | `/admin/balanced-scorecard` | `admin/balanced-scorecard/page.tsx` | **200 OK** | بطاقة الأداء المتوازن بالمحاور الأربعة، متصلة بالواجهة الخلفية. |
| 16 | `/admin/business-value` | `admin/business-value/page.tsx` | **200 OK** | لوحة عائد الاستثمار وقمع التحويل واختبارات A/B بـ SciPy، متصلة بـ 8 مسارات backend حية. |
| 17 | `/admin/catalog` | `admin/catalog/page.tsx` | **200 OK** | إدارة الأدوية والمخزون، إضافة وتعديل وحذف وتفعيل بروتوكول السحب الدوائي، متصلة بنقاط النهاية الحية. |
| 18 | `/admin/customers` | `admin/customers/page.tsx` | **200 OK** | دليل العملاء وتصنيف الشرائح، متصل بـ `/api/v1/customers/`. |
| 19 | `/admin/customers/[id]` | `admin/customers/[id]/page.tsx` | **200 OK** | بروفايل العميل 360 ومعدل الالتزام الدوائي MPR، متصل بمسارات العميل المحمية. |
| 20 | `/admin/notifications` | `admin/notifications/page.tsx` | **200 OK** | صندوق رسائل التواصل والتنبيهات السريرية، متصل بـ `/contact/admin-inbox`. |
| 21 | `/admin/orders` | `admin/orders/page.tsx` | **200 OK** | **عطل بصري:** زر أيقونة العين (`visibility`) في السطر 328 **زر ميت لا يحتوي على أي دالة onClick أو رابط**! زر الفاتورة الضريبية ETA يعمل بنجاح. |
| 22 | `/admin/prescriptions/[id]/review` | `admin/prescriptions/[id]/review/page.tsx` | **200 OK** | منصة الصيدلي لاعتماد/تعديل بنود الروشتة وتأكيد الطلب متصلة بـ `review` و `finalize`. |
| 23 | `/admin/procurement` | `admin/procurement/page.tsx` | **200 OK** | **خطأ في الرندر:** تعريف مكونات `StatusBadge` و `LifecycleStepper` داخل دالة الصفحة ينتهك قواعد React 19 ويؤدي لوميض وفقدان التركيز. الربط بـ `/procurement/*` سليم. |
| 24 | `/admin/risk-register` | `admin/risk-register/page.tsx` | **200 OK** | سجل المخاطر الطبية وحساب مؤشر المخاطر وفق ISO 31000، متصل بـ `/governance/risks`. |
| 25 | `/admin/settings` | `admin/settings/page.tsx` | **200 OK** | إعدادات النظام الحية وسلاسل نماذج LLM والعتبات السريرية، متصلة بـ `/settings/`. |
| 26 | `/admin/system-architecture` | `admin/system-architecture/page.tsx` | **200 OK** | مخطط المعمارية وحالة UAT ومحرك n8n وسجل WORM، متصل بـ `/health` و `/runtime/tools`. |

* **نتيجة البناء (`npm run build`):** نجح البناء بالكامل عبر Turbopack في 4.5 ثوانٍ لـ 30 صفحة ومسار دون أي خطأ في تجميع TypeScript.
* **فحص تحذيرات الرندر والأخطاء البرمجية (`npm run lint`):** كشف عن **5 أخطاء و55 تحذيراً**:
  - خطآن في `procurement/page.tsx:702, 707` بسبب `Cannot create components during render`.
  - 3 أخطاء بسبب حروف اقتباس غير مرمزة في `Phase2.tsx:1068` و `system-architecture/page.tsx:561`.
  - 27 تحذيراً من نوع `Calling setState synchronously within an effect can trigger cascading renders` (React 19).

---

## 4. فحص نقاط النهاية الخلفية (Backend Comprehensive Audit — 150 Operations)

تم فحص ومسح جميع نقاط النهاية الموثقة في وثيقة `OpenAPI/Swagger`:
* **إجمالي العمليات المفحوصة:** **150 عملية** عبر **135 مساراً**.
* **النقاط المحمية بالمصادقة الصارمة (117 مساراً):**
  - تطلب رموز Bearer JWT صالحة أو X-Internal-Token ورفضت كافة الطلبات غير المصرحة برموز `401 Unauthorized` أو `403 Forbidden`.
* **النقاط العامة المسموح بطلبها دون مصادقة (33 مساراً):**
  - تقتصر على فحص الصحة (`/health`)، والكتالوج المفتوح للأدوية (`/drugs/`, `/drugs/categories`, `/drugs/recommendations`)، وفحص التداخلات الدوائية لزوار الموقع (`/check-interactions`)، ونموذج الاتصال (`/customers/contact`)، **بالإضافة إلى مسار المخزون `/inventory` (الذي تبين أنه يسرب أسرار المستودع للعامة)**.
* **اختبار الإدخالات المشوهة وحصانة الخادم (Crash & Fuzzing Test):**
  - تم إرسال حزم JSON غير مطابقة ومشوهة عمداً لجميع المسارات الـ 148 في اختبار حي متوازي.
  - **معدل انهيار الخادم (500 Internal Server Error): صفر% (0 من أصل 148)**.
  - تولت نماذج Pydantic اعتراض الحزم الفاسدة والرد بخطأ التحقق المنظم `HTTP 422 Unprocessable Entity`، أو الرفض عبر طبقة الصلاحيات `HTTP 401/403`، ومحدد السرعة `HTTP 429`.

---

## 5. فحص الثغرات الأمنية الشائعة (Security Vulnerabilities Audit)

### 1. ثغرات حزم الاعتماديات (Dependencies Audit)
* **Frontend (`npm audit`):**
  - `next 16.3.0`: **حرجة (Critical)** — تنفيذ كود عن بعد غير مصرح به على خوادم Windows (`GHSA-p293-qw3h-jr36`) وثغرة في تحسين صور AVIF (`GHSA-2xp9-vwfh-vxw4`).
  - `js-yaml 4.0.0-4.3.1`: **عالية (High)** — استهلاك غير محدود للمعالج DoS (`GHSA-2883-xcg3-v3hh`).
  - `sharp <0.35.4`: **عالية (High)** — ثغرات في مكتبة `libheif` لمعالجة الصور (`GHSA-rgj7-g3m4-5g8c`).
* **Backend (`pip-audit`):**
  - الفحص الحقيقي أظهر وجود **183 ثغرة معروفة في 26 حزمة بايثون**:
    - `aiohttp (3.13.3)`: **48 ثغرة** (تشمل تنفيذ كود عشوائي عبر `CookieJar.load()`, NTLM credential leaks on Windows, وتجاوز DoS).
    - `gitpython (3.1.50)`: **26 ثغرة** (تشمل حقن إعدادات وأوامر تؤدي إلى RCE مثل CVE-2026-76221).
    - `pillow (12.2.0)`: **25 ثغرة** أمنية في معالجة ملفات الصور.
    - `starlette (0.38.6)`: **14 ثغرة** في معالجة المدخلات والـ Multipart (نواة FastAPI نفسها!).
    - `cryptography (49.0.0)`: ثغرتان (Bleichenbacher timing oracle ضد مفاتيح التشفير CVE-2026-69247).
    - `weasyprint (69.0)`: ثغرة تسريب ملفات وبيانات اعتماد الخادم عبر خرق `stylesheets/xmp_metadata`.

### 2. التحكم في الوصول ومنع الوصول غير المصرح به (Broken Access Control / IDOR)
* **الفحص الحي:** محاولة جلب بيانات عميل آخر عبر طلب مسار الإدارة:
  ```bash
  curl.exe -s -o NUL -w "%{http_code}" http://127.0.0.1:8000/api/v1/customers/00000000-0000-0000-0000-000000000001
  ```
  أرجع الخادم **401 Unauthorized**.
* عند استدعائه بتوكن عميل عادي، ترفض دالة `require_role("admin", "super_admin")` الطلب مع كود **403 Forbidden**.
* تم التأكد من عزل المستأجرين (Tenant Isolation): استعلام الخدمة يمرر دائماً `tenant_id=current_user.tenant_id` لمنع تداخل بيانات الصيدليات المختلفة.

### 3. الحماية من هجمات تزوير الطلبات (CSRF Protection)
* جميع الطلبات الحساسة (مثل `POST /api/v1/orders/` و `POST /api/v1/governance/approve`) تعتمد على رؤوس `Authorization: Bearer <JWT>` المرفقة برمجياً عبر `fetchApi`، ولا تعتمد على الكوكيز التلقائية للمتصفح، مما يجعلها **محصنة معمارياً ضد هجمات CSRF**.
* جدار CORS يرفض بشكل قاطع أي طلبات قادمة من أصول أجنبية (`Origin: https://evil-attacker.com` قوبل بـ 400 Bad Request).

### 4. بوابات المصادقة الخارجية في Supabase (OAuth Providers)
تم استدعاء مسار المصادقة لكل موفر على بيئة Supabase الحية:
* **Google:** يعيد `HTTP 302` وتوجيهاً لـ Google OAuth مع المعرف:  
  `client_id: 488693887530-4cde34g0rtivcufc2eua0hass05n2j4r.apps.googleusercontent.com`
* **GitHub:** يعيد `HTTP 302` وتوجيهاً لـ GitHub OAuth مع المعرف:  
  `client_id: Ov23liGMvoBnQxNIJcsE`
* **Facebook:** يعيد `HTTP 302` وتوجيهاً لـ Facebook OAuth مع المعرف:  
  `client_id: 1331158659173302`
* **الخلاصة:** البوابات الثلاث مهيأة ومعتمدة وليست أزراراً شكلية.

---

## 6. الاتساق مع القواعد الثابتة والصور (Hardcoding & Placeholder Consistency)

1. **الصور الفوتوغرافية العشوائية المتبقية:**
   - في [`frontend/src/hooks/useMedicineDetails.ts:15`](file:///d:/Graduation%20Project/AI-COS-Pharmacy/frontend/src/hooks/useMedicineDetails.ts#L15) و [`frontend/src/components/ui/MedicineDetailsModal.tsx:62`](file:///d:/Graduation%20Project/AI-COS-Pharmacy/frontend/src/components/ui/MedicineDetailsModal.tsx#L62):
     ```typescript
     const imageUrl = product?.image_url || '/images/image_6.jpg';
     ```
     يتم السقوط على صورة فوتوغرافية ثابتة حقيقية (`image_6.jpg`) لدواء عشوائي عند غياب الصورة، بينما المعتمد في بقية صفحات المتجر هو استخدام المكون الموحد للأيقونات المتجهة `<MedicinePlaceholder />`.
   - توجد 9 صور فوتوغرافية في مجلد `frontend/public/images/` (`image_0.jpg` إلى `image_8.jpg`) مستخدمة كملفات تجريبية سابقة.
2. **اتساق بيانات الكتالوج مع DawaaGate:**
   - تم التحقق من الكتالوج المعروض في صفحة الكتالوج والمتجر: يتم جلبه بالكامل عبر الـ API من جدول `drugs` في قاعدة البيانات (مستند إلى قاعدة بيانات DawaaGate المعتمدة بأسماء الأدوية المصرية والجرعات والأسعار الرسمية)، ولا توجد مصفوفات أدوية وهمية صلبة (Hardcoded Mock Products) داخل صفحات العرض.

---

## 7. القائمة الموحدة للمشكلات والثغرات المرصودة (مرتبة حسب الخطورة)

### 🔴 أولاً: المشكلات والثغرات الحرجة (CRITICAL)

#### 1. ثغرة تنفيذ كود عن بعد غير مصرح به في Next.js على بيئة Windows
* **المسار:** [`frontend/package.json`](file:///d:/Graduation%20Project/AI-COS-Pharmacy/frontend/package.json) (`next: 16.3.0`)
* **المعرفات الاستشارية:** `GHSA-p293-qw3h-jr36` و `GHSA-2xp9-vwfh-vxw4`
* **الدليل الفعلي:** نتيجة `npm audit`:
  ```text
  next 16.0.0 - 16.3.2 | Severity: critical
  Next.js: Unauthenticated Remote Code Execution on windows-hosted servers
  Next.js: Unauthenticated Remote Code Execution in Image Optimization API when AVIF files are used
  ```
* **الأثر المحتمل:** بما أن خادم التطوير والإنتاج الحالي يعمل على نظام Windows (`win32`)، يمكن لمهاجم استغلال معالجة المسارات لتنفيذ أوامر برمجية على الخادم دون مصادقة.
* **الحل الموصى به:** ترقية حزمة `next` إلى إصدار آمن معالج (`16.3.5+` أو أحدث).

#### 2. عطل منطقي يمنع إتمام الشراء (Checkout Blocker) لمستخدمي ميزة "إعادة التعبئة السريعة"
* **المسارات:** [`frontend/src/app/(storefront)/profile/page.tsx:342-353, 794, 870`](file:///d:/Graduation%20Project/AI-COS-Pharmacy/frontend/src/app/%28storefront%29/profile/page.tsx#L342-L353) و [`frontend/src/app/checkout/page.tsx:81-85`](file:///d:/Graduation%20Project/AI-COS-Pharmacy/frontend/src/app/checkout/page.tsx#L81-L85)
* **الدليل الفعلي:**
  في `profile/page.tsx`:
  ```typescript
  const handleQuickRefill = (drugName: string, price: number) => {
    const slug = drugName.trim().replace(/\s+/g, '-').toLowerCase();
    addItemToCart({
      id: `refill-${slug}`, // ❌ استبدال معرف UUID الحقيقي بنص slug زائف
      name: drugName,
      price: price || 35,
      quantity: 1,
      ...
    });
  }
  ```
  في `checkout/page.tsx`:
  ```typescript
  const items = cartItems.map(item => ({
    drug_id: item.id, // ❌ يرسل 'refill-concor-5mg'
    quantity: item.quantity
  }));
  ```
  في `backend/app/domains/order/schemas.py:7`:
  ```python
  class OrderItemCreate(BaseModel):
      drug_id: UUID  # ✅ يتطلب UUID صالح
  ```
* **الأثر المحتمل:** عند قيام المريض بالضغط على "إعادة التعبئة السريعة" والتوجه للدفع، يفشل الطلب قطعياً مع خطأ `HTTP 422 Unprocessable Entity` (`Input should be a valid UUID`)، مما يعطل مسار المبيعات الرئيسي للمرضى المزمنين.
* **الحل الموصى به:** تمرير `therapy.drug_id` أو `med.drug_id` الحقيقي كـ `id` في السلة بدلاً من `refill-${slug}`.

---

### 🟠 ثانياً: المشكلات والثغرات العالية الخطورة (HIGH)

#### 1. تسريب مخزون المستودع والتسعير بالكامل للعامة بدون تسجيل دخول
* **المسار:** [`backend/app/domains/inventory/router.py:18-44`](file:///d:/Graduation%20Project/AI-COS-Pharmacy/backend/app/domains/inventory/router.py#L18-L44)
* **المسارات المستهدفة:** `GET /api/v1/inventory` و `GET /api/v1/inventory/`
* **الدليل الفعلي:**
  الكود يعتمد المصادقة الاختيارية:
  ```python
  @router.get("")
  async def get_inventory(
      current_user = Depends(get_current_user_optional),
      ...
  ):
      if current_user is None:
          target_tenant_id = settings.DEFAULT_STOREFRONT_TENANT_ID
  ```
  الاستدعاء الحي بدون أي توكن:
  `curl.exe -s http://127.0.0.1:8000/api/v1/inventory`
  أرجع **HTTP 200** وقائمة بـ **116 عنصراً مخزنياً** تفصح عن:
  `stock_level`, `inventory_id`, `drug_id`, `price`, `tenant_id`.
* **الأثر المحتمل:** إفشاء أسرار العمل وحجم مخزون المستودع للمنافسين وزوار الإنترنت دون حسيب.
* **الحل الموصى به:** حصر المسار بصلاحيات الإدارة حصراً: `Depends(require_role("admin", "pharmacist", "super_admin"))`.

#### 2. وجود 183 ثغرة أمنية معروفة في حزم الباك إند (`pip-audit`)
* **المسار:** بيئة بايثون وحزم الباك إند
* **الدليل الفعلي:** تشغيل `python -m pip_audit --format=json` الفعلي:
  - `aiohttp (3.13.3)`: 48 ثغرة (RCE في `CookieJar.load()`, NTLM leak).
  - `gitpython (3.1.50)`: 26 ثغرة (RCE وحقن إعدادات).
  - `pillow (12.2.0)`: 25 ثغرة.
  - `starlette (0.38.6)`: 14 ثغرة (نواة تشغيل FastAPI).
  - `pip (25.3)`: 10 ثغرات.
  - `cryptography (49.0.0)`: ثغرتان (توقيت هجوم Bleichenbacher).
  - `weasyprint (69.0)`: ثغرة قراءة وتسريب بيانات الاعتماد.
* **الأثر المحتمل:** مخاطر سلاسل التوريد وإمكانية استغلال ثغرات المكتبات لاختراق الخادم أو إحداث هجمات حجب الخدمة (DoS).
* **الحل الموصى به:** تحديث الحزم المصابة وإصلاح ملف `requirements.txt` بتثبيت الإصدارات الآمنة.

#### 3. إنشاء مكونات React داخل حلقة التقديم (Component Creation During Render)
* **المسار:** [`frontend/src/app/admin/procurement/page.tsx:263-277, 279-307, 702, 707`](file:///d:/Graduation%20Project/AI-COS-Pharmacy/frontend/src/app/admin/procurement/page.tsx#L263-L307)
* **الدليل الفعلي:** نتيجة فحص `npm run lint`:
  ```text
  702:23 error Error: Cannot create components during render (StatusBadge)
  707:18 error Error: Cannot create components during render (LifecycleStepper)
  ```
* **الأثر المحتمل:** في React 19، إعادة تعريف دوال المكونات داخل المكون الأب يؤدي لإعادة بنائها مع كل تغيير للحالة (Re-render)، متسبباً في وميض الصفحة وفقدان تركيز حقول الإدخال، وكسر الحالة الداخلية.
* **الحل الموصى به:** نقل `StatusBadge` و `LifecycleStepper` إلى خارج دالة `ProcurementPage` واستقبال المتغيرات عبر الـ Props.

---

### 🟡 ثالثاً: المشكلات والثغرات المتوسطة (MEDIUM)

#### 1. انحراف توصيف العقد (Contract Drift) في سجل أدوات الوكلاء
* **المسار:** [`backend/app/domains/runtime/router.py:40`](file:///d:/Graduation%20Project/AI-COS-Pharmacy/backend/app/domains/runtime/router.py#L40)
* **الدليل الفعلي:**
  في `runtime/router.py`:
  ```python
  {
      "name": "finance_clv",
      "endpoint": "/api/v1/agents/finance/clv",
      "params": ["customer_name", "proposed_discount_pct"], # ❌ معامل ملغى
  }
  ```
  في المقابل، تم حذف `proposed_discount_pct` تماماً من كود الوكيل المالي [`agents/finance.py`](file:///d:/Graduation%20Project/AI-COS-Pharmacy/backend/app/domains/agents/finance.py) حيث يقوم المدير المالي بتوليد الخصم آلياً.
* **الأثر المحتمل:** أي نظام أتمتة خارجي في n8n يستكشف الأدوات عبر `/runtime/tools` سيرسل معاملاً مهملاً وغير متوافق مع المنطق الداخلي.
* **الحل الموصى به:** تحديث قائمة المعاملات في السجل لتعكس دالة `evaluate_financial_decision` الفعلية.

#### 2. ثغرات مكتبات الفرونت إند في `js-yaml` و `sharp`
* **المسار:** [`frontend/package.json`](file:///d:/Graduation%20Project/AI-COS-Pharmacy/frontend/package.json)
* **الدليل الفعلي:** تقرير `npm audit`:
  - `js-yaml 4.0.0 - 4.3.1` (High - GHSA-2883-xcg3-v3hh): عدم تقييد استهلاك المعالج عند دمج المفاتيح.
  - `sharp <0.35.4` (High - GHSA-rgj7-g3m4-5g8c): ثغرات في مكتبة `libheif`.
* **الأثر المحتمل:** استهلاك موارد السيرفر أو التسبب في انهيار عمليات معالجة الصور ومستندات YAML.
* **الحل الموصى به:** تشغيل `npm audit fix`.

#### 3. عدم توافق مكتبات الاختبارات غير المتزامنة (`pytest-asyncio` vs `pytest 8.2`)
* **المسارات:** `tests/test_customer.py`, `tests/test_events_chain.py`, `tests/test_settings.py`
* **الدليل الفعلي:**
  ```text
  AttributeError: 'FixtureDef' object has no attribute 'unittest'
  pytest_asyncio/plugin.py:321
  ```
  تسبب في تسجيل **8 أخطاء إعداد (Setup Errors)** عند تشغيل كامل حزمة الاختبارات.
* **الأثر المحتمل:** تعطل مسار الفحص الآلي المستمر (CI/CD) لاختبارات التكامل، مما يعيق التحقق السريع للمطورين.
* **الحل الموصى به:** ترقية حزمة `pytest-asyncio` إلى إصدار متوافق مع `pytest 8.2+` (`pytest-asyncio>=0.23.7`).

---

### 🟢 رابعاً: المشكلات منخفضة الخطورة والتحسينات (LOW & COSMETIC)

#### 1. وجود زر معاينة ميت (Dead Button) في جدول الطلبات
* **المسار:** [`frontend/src/app/admin/orders/page.tsx:328-330`](file:///d:/Graduation%20Project/AI-COS-Pharmacy/frontend/src/app/admin/orders/page.tsx#L328-L330)
* **الدليل الفعلي:**
  ```tsx
  <button className="text-outline hover:text-primary transition-colors p-1 rounded-full hover:bg-primary/10">
    <span className="material-symbols-outlined text-[18px]">visibility</span>
  </button>
  ```
  الزر لا يحتوي على أي خاصية `onClick` ولا يؤدي لأي فعل بصري أو برمجي عند الضغط عليه.
* **الأثر المحتمل:** تجربة مستخدم مربكة للمشرف عند محاولة معاينة الطلب.
* **الحل الموصى به:** ربط الزر بمودال تفاصيل الطلب أو تحويله إلى رابط فعال.

#### 2. السقوط على صورة فوتوغرافية ثابتة عشوائية كبديل
* **المسارات:** [`frontend/src/hooks/useMedicineDetails.ts:15`](file:///d:/Graduation%20Project/AI-COS-Pharmacy/frontend/src/hooks/useMedicineDetails.ts#L15) و [`frontend/src/components/ui/MedicineDetailsModal.tsx:62`](file:///d:/Graduation%20Project/AI-COS-Pharmacy/frontend/src/components/ui/MedicineDetailsModal.tsx#L62)
* **الدليل الفعلي:**
  `const imageUrl = product?.image_url || '/images/image_6.jpg';`
* **الأثر المحتمل:** عرض صورة علبة دواء حقيقية لا تطابق الدواء المعروض في حال عدم وجود صورة له.
* **الحل الموصى به:** استبدالها بـ `<MedicinePlaceholder category={product?.category} />`.

#### 3. حروف اقتباس غير مرمزة في JSX (Unescaped Entities)
* **المسارات:** [`frontend/src/app/admin/agentic-ai/components/Phase2.tsx:1068`](file:///d:/Graduation%20Project/AI-COS-Pharmacy/frontend/src/app/admin/agentic-ai/components/Phase2.tsx#L1068) و [`frontend/src/app/admin/system-architecture/page.tsx:561`](file:///d:/Graduation%20Project/AI-COS-Pharmacy/frontend/src/app/admin/system-architecture/page.tsx#L561)
* **الدليل الفعلي:** تسجيل 3 أخطاء في ESLint بخصوص `react/no-unescaped-entities`.
* **الحل الموصى به:** استبدال الاقتباسات بـ `&quot;` و `&apos;`.

#### 4. استخدام وسوم `<img>` تقليدية بدلاً من مكون `<Image />`
* **المسارات:** `PrescriptionModal.tsx`, `MedicineDetailsModal.tsx`, `CartDrawer.tsx`
* **الدليل الفعلي:** 55 تحذيراً في ESLint عن تأخر محتمل في مقياس LCP.
* **الحل الموصى به:** استبدال الوسوم بمكون `next/image`.

---

## 8. Remaining Questions & Gaps (الأسئلة المعلقة والفجوات)

1. **التحقق من تحديث أوزان نماذج الذكاء الاصطناعي (Ollama Weight Verification):**
   - هل نماذج Ollama المحلية (`AI-COS-Qwen-2.5` أو `gemma4:31b-cloud`) محملة من مصادر رسمية موثقة بـ Checksum ضد ثغرات Deserialization التي وردت في تقرير `accelerate`؟
2. **اختبار ترقية `next` و `pytest-asyncio` على بيئة تجريبية:**
   - ترقية `next` من 16.3.0 إلى 16.3.5+ لمعالجة ثغرة Windows RCE تتطلب اختبار توافق مع مكونات Three.js و Vanta المستخدمة في الواجهة.
3. **أولويات الفريق المطور للإصلاح بالترتيب الصارم:**
   - **الخطوة 1:** تصحيح `profile/page.tsx:344` لتمرير `drug_id: therapy.drug_id` لرفع الحظر عن إتمام الشراء فوراً.
   - **الخطوة 2:** إغلاق مسار المخزون `GET /api/v1/inventory` خلف `require_role('admin', 'pharmacist')`.
   - **الخطوة 3:** تشغيل `npm audit fix` وترقية حزمة `next` لمعالجة ثغرة Windows الحرجة.
   - **الخطوة 4:** إصلاح خطأ `Cannot create components during render` في `procurement/page.tsx`.
   - **الخطوة 5:** ربط أو إزالة زر المعاينة الميت في `admin/orders/page.tsx:328`.