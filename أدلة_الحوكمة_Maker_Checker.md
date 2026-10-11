# 🛡️ حقيبة أدلة الحوكمة — Maker/Checker · WORM · Outbox · Provenance
**مشروع AI-COS Pharmacy — تم التحقق الحي بتاريخ 2026-09-28 (الساعة 17:38 UTC)**

---

## 1️⃣ السيناريو الحي الموثق: قرار CRITICAL عبر Maker/Checker

**القرار المُختبَر:** `4dc8d995-d717-4108-a1fc-6d16345dd043` — سحب دفعة Panadol Batch #2026-EG (priority=critical)

| الخطوة | الفاعل | النتيجة الفعلية (نص السيرفر) |
|---|---|---|
| 1. Maker يعتمد | `admin_a@example.com` | ✅ `AWAITING_SECOND_APPROVAL` — *"اعتماد أول (Maker) موثق في WORM — القرار CRITICAL يستلزم اعتماداً ثانياً من مستخدم مختلف"* |
| 2. نفس الهوية تحاول مجدداً | `admin_a@example.com` | ✅ **مرفوض**: *"Maker-Checker: نفس المستخدم لا يمكنه تنفيذ الاعتمادين"* |
| 3. Checker يعتمد | `verifier_admin_2027@test.com` | ✅ *"approved and executed with WORM verification"* — نُفِّذ **مرة واحدة** |
| 4. محاولة تنفيذ مكررة | `verifier_admin_2027@test.com` | ✅ **مرفوض**: *"Action was already executed previously"* |

### الدليل المخزن في قاعدة البيانات (استعلام التحقق):
```sql
SELECT status, priority, maker_id, checker_id, approved_at, executed_at, approved_by
FROM market_intelligence_actions WHERE action_id = '4dc8d995-d717-4108-a1fc-6d16345dd043';
```
**النتيجة الفعلية:** `EXECUTED` · `critical` · `maker_id=d323a783…` · `checker_id=7745bc54…` · `approved_at = executed_at = 2026-09-28 17:38:25 UTC` · `approved_by=verifier_admin_2027`

### دليل الـ Outbox (الحدث دُلفِر مرة واحدة):
```sql
SELECT event_id, status, attempts, payload_hash, worm_line_hash
FROM market_action_outbox ORDER BY created_at DESC LIMIT 3;
```
**النتيجة الفعلية:** `event_id = MI-4dc8d995…` · `status = SENT` · `attempts = 1` · مع `payload_hash` + `worm_line_hash` (الربط بسجل WORM)

---

## 2️⃣ قرار حي جاهز للعرض أمام اللجنة

`fd2e5b96-5343-4aec-8125-277d7c027f2c` — حالة `PENDING_APPROVAL` (critical)

**السيناريو الحي (دقيقتان):**
1. سجّل دخول بـ **Maker** (admin_a) → اعتمد القرار → يظهر: *بانتظار التحقق الثاني — لم يُنفَّذ* ✋
2. سجّل خروج → دخول بـ **Checker** (verifier_admin_2027) → اعتمد → **ينفَّذ مرة واحدة** ✓
3. حاول مرة ثالثة → **مرفوض** ✓

*(كلمتا المرور للحسابين = نفس كلمة اختبار المنظومة القياسية — أو أعد ضبطها من Supabase)*

---

## 3️⃣ الإفصاح الصادق عن WORM (جملة المناقشة)

> *"سجل التدقيق عندنا **PoC محلي** بسلسلة تجزئة SHA-256 متسلسلة (كل سطر يحتوي hash السطر السابق)، وكل حدث بيرتبط خارجياً عبر **webhook n8n منفصل** — يعني أي تعديل محلي بيكشف فوراً بمقارنة النسخة الخارجية. التصميم يفصل الـ adapter بحيث الاستبدال بـ **S3 Object Lock** = تغيير مزوّد واحد، واخترنا عدم تنفيذها حالياً لأنها تكلفة تشغيلية خارج النطاق التعليمي."*

**الدليل الملموس المُعرَض جنبها:**
- `backend/external_audit_ledger.log` (362+ سطر chain-valid)
- تنفيذ workflow الـ n8n `worm-anchor` الحي (HTTP 200 anchored)

---

## 4️⃣ مراقبة Outbox بدون كود (Supabase → SQL Editor → Save)

```sql
SELECT status, COUNT(*) AS events, MIN(created_at) AS oldest, MAX(created_at) AS latest
FROM market_action_outbox
GROUP BY status ORDER BY events DESC;
```
**و الجملة:** *"ده جدول الـ Outbox الحي — أي حدث فاشل بيتحول `DEAD_LETTER` بعد المحاولات وبيتراجع يدوياً بأمان، والقرار نفسه ماينفذش مرتين أبداً."*

*(نتيجة التشغيل الفعلي: SENT = 1، attempts = 1 — التسليم من أول محاولة)*

---

## 5️⃣ Provenance إشارات السوق (بدون كود)

```sql
SELECT action_id, source, market_signal_id, status, priority, created_at
FROM market_intelligence_actions
ORDER BY created_at DESC LIMIT 10;
```
**الجملة:** *"كل قرار تنفيذي مربوط بإشارته (`market_signal_id`) ومصدره (`source`) ووقته — والقرار بلا مصدر لا يُنفَّذ."*

*(ملاحظة صدق: الإشارات تأتي من مسح Gemini مع grounding بحثي — وصفحة السوق تعرض شارة المصدر: Live / Baseline مُعايَر 2026)*

---

## 📌 الحالة التشغيلية بعد هذا التحقق

| البند | الحالة |
|---|---|
| Migrations على الإنتاج | ✅ `head = market_action_approver_ids_20260928` |
| Maker/Checker على السحابة | ✅ مُختبر حياً بأدلة |
| Outbox → WORM | ✅ SENT من أول محاولة |
| WORM immutable خارجي | ⚠️ PoC محلي — الإفصاح جاهز (S3 = خطة مستقبلية) |
| قرارات عرض حية | ✅ `fd2e5b96…` جاهز للسيناريو أمام اللجنة |
