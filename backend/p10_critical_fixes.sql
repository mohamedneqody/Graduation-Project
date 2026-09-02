-- ============================================================
-- P10 Critical Fixes — AI-COS Pharmacy
-- Run this SQL in: Supabase Dashboard → SQL Editor
-- ⚠️ Requires: Supabase service role or postgres superuser
-- ============================================================

-- ============================================================
-- GROUP 1 — BUG-01: Add missing columns to orders table
-- The ORM model declares these but the initial migration never created them.
-- Every order creation was crashing with UndefinedColumn error.
-- ============================================================

ALTER TABLE public.orders
  ADD COLUMN IF NOT EXISTS shipping_name    VARCHAR(255),
  ADD COLUMN IF NOT EXISTS shipping_phone   VARCHAR(50),
  ADD COLUMN IF NOT EXISTS shipping_address VARCHAR(500),
  ADD COLUMN IF NOT EXISTS payment_method   VARCHAR(50) NOT NULL DEFAULT 'credit_card';

-- ============================================================
-- GROUP 2 — BUG-02: Add missing clinical columns to drugs table
-- The Drug ORM model declares these but no migration created them.
-- Clinical data (dosage, warnings, active_ingredient) could never be saved.
-- ============================================================

ALTER TABLE public.drugs
  ADD COLUMN IF NOT EXISTS active_ingredient VARCHAR(255),
  ADD COLUMN IF NOT EXISTS dosage            VARCHAR(100),
  ADD COLUMN IF NOT EXISTS warnings          VARCHAR(1000);

-- ============================================================
-- GROUP 3 — BUG-03: Restore RLS SELECT policies for drug_interactions
--           and drug_affinities tables.
--
-- phase5_audit_hardening migration dropped global_read_* policies and
-- left the replacement commented out → deny-all for all app roles.
-- This broke the drug interaction safety check on every order AND
-- all cross-sell recommendations.
--
-- These tables are global (no tenant_id) by design — drug interaction
-- data is shared across tenants. A global SELECT policy is correct here.
-- ============================================================

-- drug_interactions
DROP POLICY IF EXISTS global_read_drug_interactions ON public.drug_interactions;

CREATE POLICY global_read_drug_interactions
  ON public.drug_interactions
  FOR SELECT
  USING (true);

-- drug_affinities
DROP POLICY IF EXISTS global_read_drug_affinities ON public.drug_affinities;

CREATE POLICY global_read_drug_affinities
  ON public.drug_affinities
  FOR SELECT
  USING (true);

-- ============================================================
-- VERIFICATION — Run these SELECT queries to confirm the changes:
-- ============================================================

-- Check orders columns exist:
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'orders'
  AND column_name IN ('shipping_name', 'shipping_phone', 'shipping_address', 'payment_method')
ORDER BY column_name;

-- Check drugs columns exist:
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'drugs'
  AND column_name IN ('active_ingredient', 'dosage', 'warnings')
ORDER BY column_name;

-- Check RLS policies exist on both tables:
SELECT schemaname, tablename, policyname, cmd, qual
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN ('drug_interactions', 'drug_affinities')
ORDER BY tablename, policyname;
