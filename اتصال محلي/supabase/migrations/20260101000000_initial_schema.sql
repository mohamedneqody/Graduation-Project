-- Auto-generated schema migration from Supabase Cloud
-- Project: Graduation Project (quhfheudhewxqmvxwjij)

-- Extensions (must be enabled before tables that use their types)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Sequences (must be created before tables that reference them)
CREATE SEQUENCE IF NOT EXISTS "events_event_seq_seq" START WITH 1 INCREMENT BY 1 MINVALUE 1 NO MAXVALUE;
CREATE SEQUENCE IF NOT EXISTS "emergency_outbox_id_seq" START WITH 1 INCREMENT BY 1 MINVALUE 1 NO MAXVALUE;

CREATE TABLE IF NOT EXISTS "ab_test_results" (
    "result_id" UUID DEFAULT gen_random_uuid() NOT NULL,
    "test_id" UUID NOT NULL,
    "notification_id" UUID NOT NULL,
    "variant" VARCHAR(50) NOT NULL,
    "converted" BOOLEAN DEFAULT false NOT NULL,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS "ab_tests" (
    "test_id" UUID DEFAULT gen_random_uuid() NOT NULL,
    "tenant_id" UUID NOT NULL,
    "test_name" VARCHAR(100) NOT NULL,
    "variant_a" VARCHAR(50) NOT NULL,
    "variant_b" VARCHAR(50) NOT NULL,
    "start_date" DATE NOT NULL,
    "end_date" DATE,
    "is_active" BOOLEAN DEFAULT true NOT NULL,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS "ai_chat_logs" (
    "log_id" UUID DEFAULT gen_random_uuid() NOT NULL,
    "session_id" TEXT,
    "customer_id" UUID,
    "user_prompt" TEXT NOT NULL,
    "ai_response" TEXT,
    "engines_used" text[],
    "ddi_detected" BOOLEAN DEFAULT false,
    "security_flagged" BOOLEAN DEFAULT false,
    "escalation_status" TEXT DEFAULT 'normal'::text,
    "response_time_ms" INTEGER,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT now(),
    "intent" TEXT,
    "tenant_id" UUID
);

CREATE TABLE IF NOT EXISTS "alembic_version" (
    "version_num" VARCHAR(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS "audit_logs" (
    "log_id" UUID NOT NULL,
    "tenant_id" UUID NOT NULL,
    "actor_id" VARCHAR(100) NOT NULL,
    "action_type" VARCHAR(50) NOT NULL,
    "target_entity" VARCHAR(100) NOT NULL,
    "timestamp" TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    "details" JSONB
);

CREATE TABLE IF NOT EXISTS "automation_runs" (
    "id" UUID DEFAULT gen_random_uuid() NOT NULL,
    "workflow_name" VARCHAR(64) NOT NULL,
    "tenant_id" UUID,
    "trigger_source" VARCHAR(32) DEFAULT 'manual'::character varying NOT NULL,
    "status" VARCHAR(32) DEFAULT 'pending'::character varying NOT NULL,
    "reason" VARCHAR(255),
    "n8n_detail" VARCHAR(255),
    "attempts" INTEGER DEFAULT 0 NOT NULL,
    "max_attempts" INTEGER DEFAULT 3 NOT NULL,
    "next_retry_at" TIMESTAMP WITH TIME ZONE,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    "payload" JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS "contact_messages" (
    "id" UUID DEFAULT gen_random_uuid() NOT NULL,
    "tenant_id" UUID NOT NULL,
    "customer_id" UUID,
    "first_name" VARCHAR(255) NOT NULL,
    "last_name" VARCHAR(255) NOT NULL,
    "email" VARCHAR(255) NOT NULL,
    "message" TEXT NOT NULL,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS "coupons" (
    "id" UUID DEFAULT gen_random_uuid() NOT NULL,
    "code" VARCHAR(32) NOT NULL,
    "tenant_id" UUID,
    "customer_name" VARCHAR(255),
    "discount_pct" INTEGER NOT NULL,
    "campaign_type" VARCHAR(32),
    "drug_name" VARCHAR(255),
    "channel" VARCHAR(32),
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    "expires_at" TIMESTAMP WITH TIME ZONE NOT NULL,
    "used_at" TIMESTAMP WITH TIME ZONE,
    "used_order_id" UUID
);

CREATE TABLE IF NOT EXISTS "customer_cycles" (
    "customer_id" UUID NOT NULL,
    "drug_id" UUID NOT NULL,
    "avg_cycle_days" DOUBLE PRECISION NOT NULL,
    "last_purchase_date" DATE NOT NULL,
    "reminder_day" DATE
);

CREATE TABLE IF NOT EXISTS "customers" (
    "customer_id" UUID NOT NULL,
    "auth_user_id" UUID NOT NULL,
    "tenant_id" UUID NOT NULL,
    "email" VARCHAR(255) NOT NULL,
    "full_name" VARCHAR(255),
    "phone" VARCHAR(30),
    "age_group" VARCHAR(30),
    "preferred_channel" VARCHAR(20) DEFAULT 'email'::character varying NOT NULL,
    "preferred_language" VARCHAR(10) DEFAULT 'ar'::character varying NOT NULL,
    "is_active" BOOLEAN DEFAULT true NOT NULL,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    "last_login_at" TIMESTAMP WITH TIME ZONE,
    "role" VARCHAR(50) DEFAULT 'customer'::character varying NOT NULL
);

CREATE TABLE IF NOT EXISTS "drug_affinities" (
    "affinity_id" UUID NOT NULL,
    "drug_id_a" UUID NOT NULL,
    "drug_id_b" UUID NOT NULL,
    "affinity_type" VARCHAR(20) NOT NULL,
    "confidence_score" DOUBLE PRECISION DEFAULT '0'::double precision NOT NULL
);

CREATE TABLE IF NOT EXISTS "drug_interactions" (
    "interaction_id" UUID NOT NULL,
    "drug_id_a" UUID NOT NULL,
    "drug_id_b" UUID NOT NULL,
    "severity" VARCHAR(20) NOT NULL,
    "note" VARCHAR(500)
);

CREATE TABLE IF NOT EXISTS "drugs" (
    "drug_id" UUID NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "category" VARCHAR(100) NOT NULL,
    "is_chronic" BOOLEAN DEFAULT false NOT NULL,
    "base_price" NUMERIC(10,2) NOT NULL,
    "default_cycle_days" INTEGER DEFAULT 30 NOT NULL,
    "image_url" VARCHAR(500),
    "active_ingredient" VARCHAR(255),
    "dosage" VARCHAR(100),
    "warnings" VARCHAR(1000),
    "data_source" VARCHAR(100) DEFAULT 'eda_egyptian_drug_authority'::character varying,
    "is_verified" BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS "emergency_outbox" (
    "id" INTEGER DEFAULT nextval('emergency_outbox_id_seq'::regclass) NOT NULL,
    "tenant_id" UUID,
    "payload" JSONB NOT NULL,
    "status" VARCHAR(16),
    "attempts" INTEGER,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT now(),
    "sent_at" TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS "events" (
    "event_id" UUID NOT NULL,
    "session_id" UUID NOT NULL,
    "event_type" VARCHAR(50) NOT NULL,
    "payload" JSONB,
    "timestamp" TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    "payload_hash" VARCHAR(64),
    "prev_hash" VARCHAR(64),
    "actor_id" UUID,
    "source_ip" INET,
    "user_agent" VARCHAR(200),
    "event_seq" BIGINT DEFAULT nextval('events_event_seq_seq'::regclass) NOT NULL
);

CREATE TABLE IF NOT EXISTS "inventory_items" (
    "inventory_id" UUID NOT NULL,
    "tenant_id" UUID NOT NULL,
    "drug_id" UUID NOT NULL,
    "stock_level" INTEGER NOT NULL,
    "reorder_point" INTEGER NOT NULL,
    "tenant_price" NUMERIC(10,2),
    "is_active" BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS "journal_entries" (
    "entry_id" UUID DEFAULT gen_random_uuid() NOT NULL,
    "tenant_id" UUID NOT NULL,
    "entry_number" VARCHAR(50) NOT NULL,
    "entry_date" TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    "reference_type" VARCHAR(50) NOT NULL,
    "reference_id" VARCHAR(100),
    "description_ar" TEXT NOT NULL,
    "total_debit" NUMERIC(12,2) DEFAULT 0.00 NOT NULL,
    "total_credit" NUMERIC(12,2) DEFAULT 0.00 NOT NULL,
    "is_balanced" BOOLEAN DEFAULT true NOT NULL,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS "journal_entry_lines" (
    "line_id" UUID DEFAULT gen_random_uuid() NOT NULL,
    "entry_id" UUID NOT NULL,
    "account_code" VARCHAR(20) NOT NULL,
    "account_name_ar" VARCHAR(100) NOT NULL,
    "account_type" VARCHAR(50) NOT NULL,
    "debit" NUMERIC(12,2) DEFAULT 0.00 NOT NULL,
    "credit" NUMERIC(12,2) DEFAULT 0.00 NOT NULL,
    "line_description" VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS "knowledge_chunks" (
    "chunk_id" UUID NOT NULL,
    "tenant_id" UUID NOT NULL,
    "source_type" VARCHAR(50) NOT NULL,
    "content" TEXT NOT NULL,
    "embedding" vector(384) NOT NULL,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS "notifications" (
    "notification_id" UUID NOT NULL,
    "tenant_id" UUID NOT NULL,
    "customer_id" UUID NOT NULL,
    "notification_type" VARCHAR(30) NOT NULL,
    "channel" VARCHAR(20) NOT NULL,
    "ab_variant" VARCHAR(20),
    "status" VARCHAR(20) DEFAULT 'pending'::character varying NOT NULL,
    "sent_at" TIMESTAMP WITH TIME ZONE,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS "ocr_corrections" (
    "id" UUID DEFAULT gen_random_uuid() NOT NULL,
    "tenant_id" UUID,
    "wrong_reading_norm" VARCHAR(255) NOT NULL,
    "corrected_name" VARCHAR(255) NOT NULL,
    "source" VARCHAR(32) DEFAULT 'pharmacist_override'::character varying NOT NULL,
    "hit_count" INTEGER DEFAULT 0 NOT NULL,
    "created_by" UUID,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS "order_items" (
    "order_item_id" UUID NOT NULL,
    "order_id" UUID NOT NULL,
    "drug_id" UUID NOT NULL,
    "quantity" INTEGER DEFAULT 1 NOT NULL,
    "price" NUMERIC(10,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS "orders" (
    "order_id" UUID NOT NULL,
    "tenant_id" UUID NOT NULL,
    "customer_id" UUID NOT NULL,
    "order_date" TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    "status" VARCHAR(20) DEFAULT 'completed'::character varying NOT NULL,
    "channel" VARCHAR(20) DEFAULT 'web'::character varying NOT NULL,
    "shipping_name" VARCHAR(255),
    "shipping_phone" VARCHAR(50),
    "shipping_address" TEXT,
    "payment_method" VARCHAR(50) DEFAULT 'credit_card'::character varying
);

CREATE TABLE IF NOT EXISTS "pending_reminders" (
    "reminder_id" UUID NOT NULL,
    "customer_id" UUID NOT NULL,
    "drug_id" UUID NOT NULL,
    "channel" VARCHAR(20) NOT NULL,
    "decision" VARCHAR(20) NOT NULL,
    "cycle_confidence" DOUBLE PRECISION NOT NULL,
    "churn_probability" DOUBLE PRECISION NOT NULL,
    "predicted_days" DOUBLE PRECISION NOT NULL,
    "status" VARCHAR(20) NOT NULL,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    "processed_at" TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS "prescription_analyses" (
    "id" UUID NOT NULL,
    "prescription_id" UUID NOT NULL,
    "provider" VARCHAR(100) NOT NULL,
    "model" VARCHAR(100) NOT NULL,
    "model_version" VARCHAR(100),
    "prompt_version" VARCHAR(100),
    "schema_version" VARCHAR(100),
    "request_id" VARCHAR(255),
    "latency_ms" INTEGER,
    "token_usage" JSONB,
    "raw_response" JSONB,
    "status" VARCHAR(50) DEFAULT 'pending'::character varying NOT NULL,
    "error_message" TEXT,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS "prescription_items" (
    "id" UUID NOT NULL,
    "analysis_id" UUID NOT NULL,
    "raw_name" VARCHAR(255),
    "normalized_name" VARCHAR(255),
    "strength" VARCHAR(100),
    "dosage_form" VARCHAR(100),
    "quantity" VARCHAR(100),
    "duration" VARCHAR(100),
    "instructions" VARCHAR(500),
    "ocr_confidence" DOUBLE PRECISION,
    "is_illegible" BOOLEAN DEFAULT false NOT NULL,
    "match_status" VARCHAR(50) NOT NULL,
    "matched_drug_id" UUID,
    "match_confidence" DOUBLE PRECISION,
    "candidate_margin" DOUBLE PRECISION,
    "candidates" JSONB,
    "pharmacist_decision" VARCHAR(50) DEFAULT 'pending'::character varying NOT NULL,
    "pharmacist_selected_drug_id" UUID,
    "reviewed_by" UUID,
    "reviewed_at" TIMESTAMP WITH TIME ZONE,
    "cropped_image" TEXT,
    "auto_corrected" BOOLEAN DEFAULT false NOT NULL
);

CREATE TABLE IF NOT EXISTS "prescriptions" (
    "id" UUID NOT NULL,
    "file_id" VARCHAR(255) NOT NULL,
    "uploaded_by" UUID NOT NULL,
    "status" VARCHAR(50) DEFAULT 'uploaded'::character varying NOT NULL,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    "tenant_id" UUID,
    "file_sha256" VARCHAR(64)
);

CREATE TABLE IF NOT EXISTS "purchase_order_items" (
    "item_id" UUID DEFAULT gen_random_uuid() NOT NULL,
    "po_id" UUID NOT NULL,
    "drug_id" UUID NOT NULL,
    "drug_name" VARCHAR(255) NOT NULL,
    "quantity_ordered" INTEGER NOT NULL,
    "quantity_received" INTEGER DEFAULT 0 NOT NULL,
    "unit_cost" NUMERIC(10,2) DEFAULT 0.00 NOT NULL,
    "subtotal" NUMERIC(12,2) DEFAULT 0.00 NOT NULL
);

CREATE TABLE IF NOT EXISTS "purchase_orders" (
    "po_id" UUID DEFAULT gen_random_uuid() NOT NULL,
    "tenant_id" UUID NOT NULL,
    "po_number" VARCHAR(50) NOT NULL,
    "supplier_name" VARCHAR(255) DEFAULT 'المتحدة للصيادلة (United Pharmacists)'::character varying NOT NULL,
    "status" VARCHAR(50) DEFAULT 'DRAFT'::character varying NOT NULL,
    "total_estimated_cost" NUMERIC(12,2) DEFAULT 0.00 NOT NULL,
    "created_by" VARCHAR(100) DEFAULT 'INVENTORY_AGENT_EOQ'::character varying NOT NULL,
    "notes" TEXT,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    "approved_at" TIMESTAMP WITH TIME ZONE,
    "received_at" TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS "sessions" (
    "session_id" UUID NOT NULL,
    "tenant_id" UUID NOT NULL,
    "customer_id" UUID,
    "device_info" VARCHAR(255),
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS "tenant_settings" (
    "id" UUID NOT NULL,
    "tenant_id" UUID NOT NULL,
    "ai_review_mode" BOOLEAN NOT NULL,
    "enterprise_notifications" BOOLEAN NOT NULL,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    "cloud_ocr_allowed" BOOLEAN DEFAULT false NOT NULL
);

CREATE TABLE IF NOT EXISTS "tenants" (
    "tenant_id" UUID NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "subdomain" VARCHAR(100) NOT NULL,
    "is_active" BOOLEAN DEFAULT true NOT NULL,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

-- Primary Keys
ALTER TABLE "ab_test_results" ADD CONSTRAINT "ab_test_results_pkey" PRIMARY KEY ("result_id");
ALTER TABLE "ab_tests" ADD CONSTRAINT "ab_tests_pkey" PRIMARY KEY ("test_id");
ALTER TABLE "ai_chat_logs" ADD CONSTRAINT "ai_chat_logs_pkey" PRIMARY KEY ("log_id");
ALTER TABLE "alembic_version" ADD CONSTRAINT "alembic_version_pkc" PRIMARY KEY ("version_num");
ALTER TABLE "audit_logs" ADD CONSTRAINT "audit_logs_pkey" PRIMARY KEY ("log_id");
ALTER TABLE "automation_runs" ADD CONSTRAINT "automation_runs_pkey" PRIMARY KEY ("id");
ALTER TABLE "contact_messages" ADD CONSTRAINT "contact_messages_pkey" PRIMARY KEY ("id");
ALTER TABLE "coupons" ADD CONSTRAINT "coupons_pkey" PRIMARY KEY ("id");
ALTER TABLE "customer_cycles" ADD CONSTRAINT "customer_cycles_pkey" PRIMARY KEY ("customer_id", "drug_id");
ALTER TABLE "customers" ADD CONSTRAINT "customers_pkey" PRIMARY KEY ("customer_id");
ALTER TABLE "drug_affinities" ADD CONSTRAINT "drug_affinities_pkey" PRIMARY KEY ("affinity_id");
ALTER TABLE "drug_interactions" ADD CONSTRAINT "drug_interactions_pkey" PRIMARY KEY ("interaction_id");
ALTER TABLE "drugs" ADD CONSTRAINT "drugs_pkey" PRIMARY KEY ("drug_id");
ALTER TABLE "emergency_outbox" ADD CONSTRAINT "emergency_outbox_pkey" PRIMARY KEY ("id");
ALTER TABLE "events" ADD CONSTRAINT "events_pkey" PRIMARY KEY ("event_id");
ALTER TABLE "inventory_items" ADD CONSTRAINT "inventory_items_pkey" PRIMARY KEY ("inventory_id");
ALTER TABLE "journal_entries" ADD CONSTRAINT "journal_entries_pkey" PRIMARY KEY ("entry_id");
ALTER TABLE "journal_entry_lines" ADD CONSTRAINT "journal_entry_lines_pkey" PRIMARY KEY ("line_id");
ALTER TABLE "knowledge_chunks" ADD CONSTRAINT "knowledge_chunks_pkey" PRIMARY KEY ("chunk_id");
ALTER TABLE "notifications" ADD CONSTRAINT "notifications_pkey" PRIMARY KEY ("notification_id");
ALTER TABLE "ocr_corrections" ADD CONSTRAINT "ocr_corrections_pkey" PRIMARY KEY ("id");
ALTER TABLE "order_items" ADD CONSTRAINT "order_items_pkey" PRIMARY KEY ("order_item_id");
ALTER TABLE "orders" ADD CONSTRAINT "orders_pkey" PRIMARY KEY ("order_id");
ALTER TABLE "pending_reminders" ADD CONSTRAINT "pending_reminders_pkey" PRIMARY KEY ("reminder_id");
ALTER TABLE "prescription_analyses" ADD CONSTRAINT "prescription_analyses_pkey" PRIMARY KEY ("id");
ALTER TABLE "prescription_items" ADD CONSTRAINT "prescription_items_pkey" PRIMARY KEY ("id");
ALTER TABLE "prescriptions" ADD CONSTRAINT "prescriptions_pkey" PRIMARY KEY ("id");
ALTER TABLE "purchase_order_items" ADD CONSTRAINT "purchase_order_items_pkey" PRIMARY KEY ("item_id");
ALTER TABLE "purchase_orders" ADD CONSTRAINT "purchase_orders_pkey" PRIMARY KEY ("po_id");
ALTER TABLE "sessions" ADD CONSTRAINT "sessions_pkey" PRIMARY KEY ("session_id");
ALTER TABLE "tenant_settings" ADD CONSTRAINT "tenant_settings_pkey" PRIMARY KEY ("id");
ALTER TABLE "tenants" ADD CONSTRAINT "tenants_pkey" PRIMARY KEY ("tenant_id");

-- Foreign Keys
ALTER TABLE "ab_test_results" ADD CONSTRAINT "ab_test_results_notification_id_fkey" FOREIGN KEY ("notification_id") REFERENCES "notifications"("notification_id");
ALTER TABLE "ab_test_results" ADD CONSTRAINT "ab_test_results_test_id_fkey" FOREIGN KEY ("test_id") REFERENCES "ab_tests"("test_id");
ALTER TABLE "ab_tests" ADD CONSTRAINT "ab_tests_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "tenants"("tenant_id");
ALTER TABLE "audit_logs" ADD CONSTRAINT "audit_logs_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "tenants"("tenant_id");
ALTER TABLE "contact_messages" ADD CONSTRAINT "contact_messages_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "tenants"("tenant_id");
ALTER TABLE "customer_cycles" ADD CONSTRAINT "customer_cycles_customer_id_fkey" FOREIGN KEY ("customer_id") REFERENCES "customers"("customer_id");
ALTER TABLE "customer_cycles" ADD CONSTRAINT "customer_cycles_drug_id_fkey" FOREIGN KEY ("drug_id") REFERENCES "drugs"("drug_id");
ALTER TABLE "customers" ADD CONSTRAINT "customers_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "tenants"("tenant_id");
ALTER TABLE "drug_affinities" ADD CONSTRAINT "drug_affinities_drug_id_a_fkey" FOREIGN KEY ("drug_id_a") REFERENCES "drugs"("drug_id");
ALTER TABLE "drug_affinities" ADD CONSTRAINT "drug_affinities_drug_id_b_fkey" FOREIGN KEY ("drug_id_b") REFERENCES "drugs"("drug_id");
ALTER TABLE "drug_interactions" ADD CONSTRAINT "drug_interactions_drug_id_b_fkey" FOREIGN KEY ("drug_id_b") REFERENCES "drugs"("drug_id");
ALTER TABLE "drug_interactions" ADD CONSTRAINT "drug_interactions_drug_id_a_fkey" FOREIGN KEY ("drug_id_a") REFERENCES "drugs"("drug_id");
ALTER TABLE "events" ADD CONSTRAINT "events_session_id_fkey" FOREIGN KEY ("session_id") REFERENCES "sessions"("session_id");
ALTER TABLE "inventory_items" ADD CONSTRAINT "inventory_items_drug_id_fkey" FOREIGN KEY ("drug_id") REFERENCES "drugs"("drug_id");
ALTER TABLE "inventory_items" ADD CONSTRAINT "inventory_items_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "tenants"("tenant_id");
ALTER TABLE "journal_entry_lines" ADD CONSTRAINT "journal_entry_lines_entry_id_fkey" FOREIGN KEY ("entry_id") REFERENCES "journal_entries"("entry_id") ON DELETE CASCADE;
ALTER TABLE "notifications" ADD CONSTRAINT "notifications_customer_id_fkey" FOREIGN KEY ("customer_id") REFERENCES "customers"("customer_id");
ALTER TABLE "notifications" ADD CONSTRAINT "notifications_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "tenants"("tenant_id");
ALTER TABLE "order_items" ADD CONSTRAINT "order_items_order_id_fkey" FOREIGN KEY ("order_id") REFERENCES "orders"("order_id");
ALTER TABLE "order_items" ADD CONSTRAINT "order_items_drug_id_fkey" FOREIGN KEY ("drug_id") REFERENCES "drugs"("drug_id");
ALTER TABLE "orders" ADD CONSTRAINT "orders_customer_id_fkey" FOREIGN KEY ("customer_id") REFERENCES "customers"("customer_id");
ALTER TABLE "orders" ADD CONSTRAINT "orders_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "tenants"("tenant_id");
ALTER TABLE "pending_reminders" ADD CONSTRAINT "pending_reminders_customer_id_fkey" FOREIGN KEY ("customer_id") REFERENCES "customers"("customer_id");
ALTER TABLE "pending_reminders" ADD CONSTRAINT "pending_reminders_drug_id_fkey" FOREIGN KEY ("drug_id") REFERENCES "drugs"("drug_id");
ALTER TABLE "prescription_analyses" ADD CONSTRAINT "prescription_analyses_prescription_id_fkey" FOREIGN KEY ("prescription_id") REFERENCES "prescriptions"("id");
ALTER TABLE "prescription_items" ADD CONSTRAINT "prescription_items_analysis_id_fkey" FOREIGN KEY ("analysis_id") REFERENCES "prescription_analyses"("id");
ALTER TABLE "prescription_items" ADD CONSTRAINT "prescription_items_matched_drug_id_fkey" FOREIGN KEY ("matched_drug_id") REFERENCES "drugs"("drug_id");
ALTER TABLE "prescription_items" ADD CONSTRAINT "prescription_items_pharmacist_selected_drug_id_fkey" FOREIGN KEY ("pharmacist_selected_drug_id") REFERENCES "drugs"("drug_id");
ALTER TABLE "purchase_order_items" ADD CONSTRAINT "purchase_order_items_drug_id_fkey" FOREIGN KEY ("drug_id") REFERENCES "drugs"("drug_id");
ALTER TABLE "purchase_order_items" ADD CONSTRAINT "purchase_order_items_po_id_fkey" FOREIGN KEY ("po_id") REFERENCES "purchase_orders"("po_id") ON DELETE CASCADE;
ALTER TABLE "sessions" ADD CONSTRAINT "sessions_customer_id_fkey" FOREIGN KEY ("customer_id") REFERENCES "customers"("customer_id");
ALTER TABLE "tenant_settings" ADD CONSTRAINT "tenant_settings_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "tenants"("tenant_id") ON DELETE CASCADE;

-- Indexes
CREATE INDEX IF NOT EXISTS ix_ab_test_results_test_id ON public.ab_test_results USING btree (test_id);
CREATE INDEX IF NOT EXISTS ix_ab_tests_tenant_id ON public.ab_tests USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_ai_chat_logs_created ON public.ai_chat_logs USING btree (created_at);
CREATE INDEX IF NOT EXISTS idx_ai_chat_logs_session ON public.ai_chat_logs USING btree (session_id);
CREATE INDEX IF NOT EXISTS idx_ai_chat_logs_tenant_created ON public.ai_chat_logs USING btree (tenant_id, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS alembic_version_pkc ON public.alembic_version USING btree (version_num);
CREATE INDEX IF NOT EXISTS ix_audit_logs_tenant_id ON public.audit_logs USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_auto_runs_retry ON public.automation_runs USING btree (next_retry_at) WHERE ((status)::text = ANY ((ARRAY['trigger_failed'::character varying, 'pending'::character varying])::text[]));
CREATE INDEX IF NOT EXISTS idx_auto_runs_wf ON public.automation_runs USING btree (workflow_name, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_contact_messages_tenant_id ON public.contact_messages USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_coupons_code ON public.coupons USING btree (code);
CREATE INDEX IF NOT EXISTS idx_coupons_expiry ON public.coupons USING btree (expires_at);
CREATE INDEX IF NOT EXISTS idx_coupons_tenant ON public.coupons USING btree (tenant_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_customers_auth_user_id ON public.customers USING btree (auth_user_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_customers_email ON public.customers USING btree (email);
CREATE INDEX IF NOT EXISTS ix_customers_tenant_id ON public.customers USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_affinity_drug_b ON public.drug_affinities USING btree (drug_id_b);
CREATE INDEX IF NOT EXISTS idx_affinity_drug_b_score ON public.drug_affinities USING btree (drug_id_b, confidence_score DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_affinity_pair ON public.drug_affinities USING btree (drug_id_a, drug_id_b);
CREATE UNIQUE INDEX IF NOT EXISTS uq_interaction_pair ON public.drug_interactions USING btree (drug_id_a, drug_id_b);
CREATE INDEX IF NOT EXISTS idx_drugs_name ON public.drugs USING btree (name);
CREATE INDEX IF NOT EXISTS ix_drugs_category ON public.drugs USING btree (category);
CREATE INDEX IF NOT EXISTS ix_events_event_seq ON public.events USING btree (event_seq);
CREATE INDEX IF NOT EXISTS ix_events_session_id ON public.events USING btree (session_id);
CREATE INDEX IF NOT EXISTS ix_inventory_items_drug_id ON public.inventory_items USING btree (drug_id);
CREATE INDEX IF NOT EXISTS ix_inventory_items_tenant_id ON public.inventory_items USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_jv_ref ON public.journal_entries USING btree (reference_type, reference_id);
CREATE INDEX IF NOT EXISTS idx_jv_tenant ON public.journal_entries USING btree (tenant_id);
CREATE UNIQUE INDEX IF NOT EXISTS journal_entries_entry_number_key ON public.journal_entries USING btree (entry_number);
CREATE INDEX IF NOT EXISTS idx_jvl_account ON public.journal_entry_lines USING btree (account_code);
CREATE INDEX IF NOT EXISTS idx_jvl_entry ON public.journal_entry_lines USING btree (entry_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_embedding_hnsw ON public.knowledge_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_tenant_id ON public.knowledge_chunks USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_tenant_id ON public.knowledge_chunks USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS ix_notifications_customer_id ON public.notifications USING btree (customer_id);
CREATE INDEX IF NOT EXISTS ix_notifications_tenant_id ON public.notifications USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_ocr_corrections_lookup ON public.ocr_corrections USING btree (tenant_id, wrong_reading_norm);
CREATE UNIQUE INDEX IF NOT EXISTS ocr_corrections_tenant_id_wrong_reading_norm_key ON public.ocr_corrections USING btree (tenant_id, wrong_reading_norm);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON public.order_items USING btree (order_id);
CREATE INDEX IF NOT EXISTS ix_order_items_drug_id ON public.order_items USING btree (drug_id);
CREATE INDEX IF NOT EXISTS ix_order_items_order_id ON public.order_items USING btree (order_id);
CREATE INDEX IF NOT EXISTS idx_orders_date_status ON public.orders USING btree (order_date DESC, status);
CREATE INDEX IF NOT EXISTS ix_orders_customer_id ON public.orders USING btree (customer_id);
CREATE INDEX IF NOT EXISTS ix_orders_tenant_id ON public.orders USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS ix_pending_reminders_customer_id ON public.pending_reminders USING btree (customer_id);
CREATE INDEX IF NOT EXISTS ix_prescription_analyses_prescription_id ON public.prescription_analyses USING btree (prescription_id);
CREATE INDEX IF NOT EXISTS ix_prescription_items_analysis_id ON public.prescription_items USING btree (analysis_id);
CREATE INDEX IF NOT EXISTS idx_poi_drug ON public.purchase_order_items USING btree (drug_id);
CREATE INDEX IF NOT EXISTS idx_poi_po ON public.purchase_order_items USING btree (po_id);
CREATE INDEX IF NOT EXISTS idx_po_status ON public.purchase_orders USING btree (status);
CREATE INDEX IF NOT EXISTS idx_po_tenant ON public.purchase_orders USING btree (tenant_id);
CREATE UNIQUE INDEX IF NOT EXISTS purchase_orders_po_number_key ON public.purchase_orders USING btree (po_number);
CREATE INDEX IF NOT EXISTS ix_sessions_customer_id ON public.sessions USING btree (customer_id);
CREATE INDEX IF NOT EXISTS ix_sessions_tenant_id ON public.sessions USING btree (tenant_id);
CREATE UNIQUE INDEX IF NOT EXISTS tenant_settings_tenant_id_key ON public.tenant_settings USING btree (tenant_id);
CREATE UNIQUE INDEX IF NOT EXISTS tenants_subdomain_key ON public.tenants USING btree (subdomain);

-- Custom Functions (required by RLS policies)
CREATE OR REPLACE FUNCTION public.current_user_tenant_id()
 RETURNS uuid
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
          SELECT COALESCE(
            NULLIF(current_setting('app.current_tenant_id', true), '')::uuid,
            (SELECT tenant_id FROM public.customers
             WHERE auth_user_id = auth.uid() LIMIT 1)
          );
        $function$;

-- Custom Roles
DO $X$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'aicos_app') THEN
    CREATE ROLE aicos_app;
  END IF;
END
$X$;

-- Enable RLS
ALTER TABLE "ab_test_results" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "ab_tests" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "ai_chat_logs" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "audit_logs" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "automation_runs" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "contact_messages" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "coupons" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "customer_cycles" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "customers" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "drug_affinities" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "drug_interactions" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "drugs" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "emergency_outbox" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "events" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "inventory_items" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "knowledge_chunks" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "notifications" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "order_items" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "orders" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "pending_reminders" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "prescription_analyses" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "prescription_items" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "prescriptions" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "sessions" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "tenant_settings" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "tenants" ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "tenant_isolation_ab_test_results" ON "ab_test_results" AS PERMISSIVE FOR ALL TO public USING ((EXISTS ( SELECT 1
   FROM ab_tests t
  WHERE ((t.test_id = ab_test_results.test_id) AND (t.tenant_id = current_user_tenant_id()))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM ab_tests t
  WHERE ((t.test_id = ab_test_results.test_id) AND (t.tenant_id = current_user_tenant_id())))));
CREATE POLICY "tenant_isolation_ab_tests" ON "ab_tests" AS PERMISSIVE FOR ALL TO public USING (((tenant_id = current_user_tenant_id()) OR (current_user_tenant_id() IS NULL))) WITH CHECK (((tenant_id = current_user_tenant_id()) OR (current_user_tenant_id() IS NULL)));
CREATE POLICY "tenant_isolation_ai_chat_logs" ON "ai_chat_logs" AS PERMISSIVE FOR ALL TO public USING (((tenant_id)::text = current_setting('app.current_tenant_id'::text, true))) WITH CHECK (((tenant_id)::text = current_setting('app.current_tenant_id'::text, true)));
CREATE POLICY "tenant_isolation_audit_logs" ON "audit_logs" AS PERMISSIVE FOR ALL TO public USING (((tenant_id = current_user_tenant_id()) OR (current_user_tenant_id() IS NULL))) WITH CHECK (((tenant_id = current_user_tenant_id()) OR (current_user_tenant_id() IS NULL)));
CREATE POLICY "automation_runs_tenant_isolation" ON "automation_runs" AS PERMISSIVE FOR ALL TO public USING (((tenant_id)::text = current_setting('app.current_tenant_id'::text, true)));
CREATE POLICY "Allow app to insert contact messages" ON "contact_messages" AS PERMISSIVE FOR INSERT TO aicos_app WITH CHECK (true);
CREATE POLICY "Service role has full access" ON "contact_messages" AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Users can insert their own contact messages" ON "contact_messages" AS PERMISSIVE FOR INSERT TO public WITH CHECK (((auth.uid() = customer_id) OR (customer_id IS NULL)));
CREATE POLICY "public_insert_contact_messages" ON "contact_messages" AS PERMISSIVE FOR INSERT TO public WITH CHECK (true);
CREATE POLICY "tenant_isolation_contact_messages" ON "contact_messages" AS PERMISSIVE FOR SELECT TO public USING (((tenant_id = current_user_tenant_id()) OR (current_user_tenant_id() IS NULL)));
CREATE POLICY "coupons_tenant_isolation" ON "coupons" AS PERMISSIVE FOR ALL TO public USING (((tenant_id)::text = current_setting('app.current_tenant_id'::text, true)));
CREATE POLICY "tenant_isolation_customer_cycles" ON "customer_cycles" AS PERMISSIVE FOR ALL TO public USING ((EXISTS ( SELECT 1
   FROM customers c
  WHERE ((c.customer_id = customer_cycles.customer_id) AND ((c.tenant_id = current_user_tenant_id()) OR (current_user_tenant_id() IS NULL)))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM customers c
  WHERE ((c.customer_id = customer_cycles.customer_id) AND ((c.tenant_id = current_user_tenant_id()) OR (current_user_tenant_id() IS NULL))))));
CREATE POLICY "Allow app to provision customers" ON "customers" AS PERMISSIVE FOR INSERT TO aicos_app WITH CHECK (true);
CREATE POLICY "Allow app to read and update self" ON "customers" AS PERMISSIVE FOR ALL TO aicos_app USING (((auth_user_id)::text = current_setting('app.current_auth_user_id'::text, true)));
CREATE POLICY "Allow app to update customers in tenant" ON "customers" AS PERMISSIVE FOR UPDATE TO aicos_app USING (((tenant_id = (NULLIF(current_setting('app.current_tenant_id'::text, true), ''::text))::uuid) OR ((auth_user_id)::text = current_setting('app.current_auth_user_id'::text, true)))) WITH CHECK (((tenant_id = (NULLIF(current_setting('app.current_tenant_id'::text, true), ''::text))::uuid) OR ((auth_user_id)::text = current_setting('app.current_auth_user_id'::text, true))));
CREATE POLICY "tenant_isolation_customers" ON "customers" AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_user_tenant_id()));
CREATE POLICY "global_read_drug_affinities" ON "drug_affinities" AS PERMISSIVE FOR SELECT TO public USING (true);
CREATE POLICY "global_read_drug_interactions" ON "drug_interactions" AS PERMISSIVE FOR SELECT TO public USING (true);
CREATE POLICY "global_read_drugs" ON "drugs" AS PERMISSIVE FOR SELECT TO public USING (true);
CREATE POLICY "tenant_isolation_emergency_outbox" ON "emergency_outbox" AS PERMISSIVE FOR ALL TO public USING (((tenant_id = current_user_tenant_id()) OR (current_user_tenant_id() IS NULL))) WITH CHECK (((tenant_id = current_user_tenant_id()) OR (current_user_tenant_id() IS NULL)));
CREATE POLICY "tenant_isolation_events" ON "events" AS PERMISSIVE FOR ALL TO public USING ((EXISTS ( SELECT 1
   FROM (sessions s
     JOIN customers c ON ((c.customer_id = s.customer_id)))
  WHERE ((s.session_id = events.session_id) AND (c.tenant_id = current_user_tenant_id()))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM (sessions s
     JOIN customers c ON ((c.customer_id = s.customer_id)))
  WHERE ((s.session_id = events.session_id) AND (c.tenant_id = current_user_tenant_id())))));
CREATE POLICY "tenant_isolation_inventory" ON "inventory_items" AS PERMISSIVE FOR SELECT TO public USING (((tenant_id)::text = current_setting('app.current_tenant_id'::text, true)));
CREATE POLICY "tenant_isolation_inventory_items" ON "inventory_items" AS PERMISSIVE FOR ALL TO public USING (((tenant_id = current_user_tenant_id()) OR (current_user_tenant_id() IS NULL))) WITH CHECK (((tenant_id = current_user_tenant_id()) OR (current_user_tenant_id() IS NULL)));
CREATE POLICY "tenant_isolation_knowledge_chunks" ON "knowledge_chunks" AS PERMISSIVE FOR ALL TO public USING (((tenant_id = current_user_tenant_id()) OR (current_user_tenant_id() IS NULL))) WITH CHECK (((tenant_id = current_user_tenant_id()) OR (current_user_tenant_id() IS NULL)));
CREATE POLICY "tenant_isolation_notifications" ON "notifications" AS PERMISSIVE FOR ALL TO public USING (((tenant_id = current_user_tenant_id()) OR (current_user_tenant_id() IS NULL))) WITH CHECK (((tenant_id = current_user_tenant_id()) OR (current_user_tenant_id() IS NULL)));
CREATE POLICY "tenant_isolation_order_items" ON "order_items" AS PERMISSIVE FOR ALL TO public USING ((EXISTS ( SELECT 1
   FROM orders o
  WHERE ((o.order_id = order_items.order_id) AND (o.tenant_id = current_user_tenant_id()))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM orders o
  WHERE ((o.order_id = order_items.order_id) AND (o.tenant_id = current_user_tenant_id())))));
CREATE POLICY "tenant_isolation_orders" ON "orders" AS PERMISSIVE FOR ALL TO public USING ((tenant_id = current_user_tenant_id()));
CREATE POLICY "tenant_isolation_pending_reminders" ON "pending_reminders" AS PERMISSIVE FOR ALL TO public USING ((EXISTS ( SELECT 1
   FROM customers c
  WHERE ((c.customer_id = pending_reminders.customer_id) AND ((c.tenant_id = current_user_tenant_id()) OR (current_user_tenant_id() IS NULL)))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM customers c
  WHERE ((c.customer_id = pending_reminders.customer_id) AND ((c.tenant_id = current_user_tenant_id()) OR (current_user_tenant_id() IS NULL))))));
CREATE POLICY "deny_anon" ON "prescription_analyses" AS PERMISSIVE FOR ALL TO public USING (false);
CREATE POLICY "deny_anon" ON "prescription_items" AS PERMISSIVE FOR ALL TO public USING (false);
CREATE POLICY "tenant_isolation" ON "prescriptions" AS PERMISSIVE FOR ALL TO public USING (((tenant_id)::text = current_setting('app.current_tenant_id'::text, true))) WITH CHECK (((tenant_id)::text = current_setting('app.current_tenant_id'::text, true)));
CREATE POLICY "tenant_isolation_sessions" ON "sessions" AS PERMISSIVE FOR ALL TO public USING ((tenant_id = current_user_tenant_id())) WITH CHECK ((tenant_id = current_user_tenant_id()));
CREATE POLICY "tenant_settings_isolation" ON "tenant_settings" AS PERMISSIVE FOR ALL TO public USING (((tenant_id = current_user_tenant_id()) OR (tenant_id = (NULLIF(current_setting('app.current_tenant_id'::text, true), ''::text))::uuid))) WITH CHECK (((tenant_id = current_user_tenant_id()) OR (tenant_id = (NULLIF(current_setting('app.current_tenant_id'::text, true), ''::text))::uuid)));
CREATE POLICY "Allow app to read active tenants for routing" ON "tenants" AS PERMISSIVE FOR SELECT TO aicos_app USING ((is_active = true));
CREATE POLICY "allow_read_active_tenants" ON "tenants" AS PERMISSIVE FOR SELECT TO public USING ((is_active = true));
CREATE POLICY "tenant_isolation_tenants" ON "tenants" AS PERMISSIVE FOR ALL TO public USING (((tenant_id = current_user_tenant_id()) OR (current_user_tenant_id() IS NULL))) WITH CHECK (((tenant_id = current_user_tenant_id()) OR (current_user_tenant_id() IS NULL)));
