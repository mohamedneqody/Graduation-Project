-- ═══════════════════════════════════════════════════════════
-- Generic DW Generator — AI-COS Pharmacy
-- المولّد الديناميكي لمستودعات البيانات (نُفِّذ حيًا على الإنتاج: 2026-10-01)
-- الملف المرجعي الكامل: المولد_والأدلة.md
-- ═══════════════════════════════════════════════════════════

-- 1) سكيما المستودع
CREATE SCHEMA IF NOT EXISTS dw;

-- 2) بُعد التاريخ (2024 → 2027 — بأسماء عربي + نهاية أسبوع مصر)
DROP TABLE IF EXISTS dw.dim_date;
CREATE TABLE dw.dim_date AS
SELECT (d)::date AS full_date,
       to_char(d,'YYYYMMDD')::int AS date_key,
       EXTRACT(YEAR FROM d)::int  AS year,
       EXTRACT(QUARTER FROM d)::int AS quarter,
       EXTRACT(MONTH FROM d)::int AS month,
       CASE EXTRACT(MONTH FROM d)
         WHEN 1 THEN 'يناير' WHEN 2 THEN 'فبراير' WHEN 3 THEN 'مارس'
         WHEN 4 THEN 'أبريل' WHEN 5 THEN 'مايو' WHEN 6 THEN 'يونيو'
         WHEN 7 THEN 'يوليو' WHEN 8 THEN 'أغسطس' WHEN 9 THEN 'سبتمبر'
         WHEN 10 THEN 'أكتوبر' WHEN 11 THEN 'نوفمبر' ELSE 'ديسمبر' END AS month_ar,
       EXTRACT(DAY FROM d)::int AS day,
       CASE WHEN EXTRACT(DOW FROM d) IN (5,6) THEN true ELSE false END AS is_weekend_eg
FROM generate_series('2024-01-01'::date, '2027-12-31'::date, '1 day') d;
ALTER TABLE dw.dim_date ADD PRIMARY KEY (full_date);
CREATE INDEX ON dw.dim_date (date_key);

-- 3) العدسات القاعدية (Generic)
CREATE OR REPLACE VIEW dw.dim_customer AS
SELECT customer_id, full_name, email, preferred_channel, preferred_language,
       created_at, last_login_at, tenant_id
FROM customers;

CREATE OR REPLACE VIEW dw.dim_product AS
SELECT drug_id AS product_id, name AS product_name, category,
       base_price, is_chronic, vertical, is_verified
FROM drugs;

CREATE OR REPLACE VIEW dw.fact_sales AS
SELECT oi.order_item_id AS sale_line_id,
       o.order_id, o.tenant_id,
       d.vertical,
       o.customer_id, oi.drug_id AS product_id,
       (o.order_date AT TIME ZONE 'Africa/Cairo')::date AS full_date,
       to_char((o.order_date AT TIME ZONE 'Africa/Cairo'),'YYYYMMDD')::int AS date_key,
       oi.quantity, oi.price AS unit_price,
       (oi.quantity * oi.price) AS line_total
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
JOIN drugs  d ON d.drug_id  = oi.drug_id;

-- 4) سجل التوليد
CREATE TABLE IF NOT EXISTS dw.generator_registry (
    vertical text PRIMARY KEY,
    generated_at timestamptz DEFAULT now(),
    objects_created text
);

-- 5) ═══ المولّد الديناميكي ═══
CREATE OR REPLACE FUNCTION dw_generate_warehouse(p_vertical text)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
    v_clean text;
    v_fact_rows bigint;
BEGIN
    v_clean := lower(regexp_replace(p_vertical, '[^a-zA-Z0-9_]', '_', 'g'));
    IF v_clean !~ '^[a-z_][a-z_]{1,29}$' THEN
        RAISE EXCEPTION 'اسم عمودي غير صالح: %', p_vertical;
    END IF;

    EXECUTE format('DROP VIEW IF EXISTS dw.%I_fact_sales', v_clean);
    EXECUTE format('CREATE VIEW dw.%I_fact_sales AS SELECT * FROM dw.fact_sales WHERE vertical = %L', v_clean, v_clean);

    EXECUTE format('DROP VIEW IF EXISTS dw.%I_dim_product', v_clean);
    EXECUTE format('CREATE VIEW dw.%I_dim_product AS SELECT * FROM dw.dim_product WHERE vertical = %L', v_clean, v_clean);

    EXECUTE format('SELECT COUNT(*) FROM dw.%I_fact_sales', v_clean) INTO v_fact_rows;

    INSERT INTO dw.generator_registry (vertical, generated_at, objects_created)
    VALUES (v_clean, now(), 'fact_sales + dim_product')
    ON CONFLICT (vertical) DO UPDATE SET generated_at = now();

    RETURN format('تم توليد مستودع «%s»: fact_sales + dim_product | صفوف الحقائق الحالية: %s', v_clean, v_fact_rows);
END $$;

-- 6) التوليد الفعلي (التنفيذ الحي الموثق)
SELECT dw_generate_warehouse('pharmacy');
SELECT dw_generate_warehouse('coffee');
SELECT dw_generate_warehouse('apparel');
SELECT dw_generate_warehouse('perfume');   -- إثبات Genericity بعمودي وهمي

-- 7) عينة تحليل حية (الصيدلية)
SELECT p.product_name, SUM(f.line_total)::numeric(12,2) AS revenue, SUM(f.quantity) AS qty
FROM dw.pharmacy_fact_sales f JOIN dw.pharmacy_dim_product p ON p.product_id = f.product_id
GROUP BY p.product_name ORDER BY revenue DESC LIMIT 5;
