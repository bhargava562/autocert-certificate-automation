-- ====================================================================================
-- Migration: 20260907000001_initial_erd_schema.sql
-- Description: Initial database schema for Autocert Certificate Automation Backend
-- Matches the 9 core ERD tables:
--   1. data_sources
--   2. batches
--   3. batch_progress
--   4. participants (immutable snapshot)
--   5. generation_tasks (task-level retry)
--   6. certificates
--   7. delivery_tasks (idempotency key)
--   8. deliveries (provider logs / zero-log troubleshooting)
--   9. previews (approval evidence)
-- ====================================================================================

-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. ENUM TYPES
DO $$ BEGIN
    CREATE TYPE source_type_enum AS ENUM (
        'CSV',
        'GOOGLE_SHEET',
        'GOOGLE_FORM',
        'MANUAL_FORM'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE batch_status_enum AS ENUM (
        'CREATED',
        'IMPORTING',
        'VALIDATING',
        'READY_FOR_GENERATION',
        'GENERATING',
        'GENERATED',
        'AWAITING_APPROVAL',
        'SENDING',
        'COMPLETED',
        'PARTIAL_SUCCESS',
        'FAILED',
        'CANCELLED'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE validation_status_enum AS ENUM (
        'PENDING',
        'VALID',
        'INVALID'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE task_status_enum AS ENUM (
        'PENDING',
        'PROCESSING',
        'COMPLETED',
        'FAILED',
        'CANCELLED'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE delivery_status_enum AS ENUM (
        'PENDING',
        'SENT',
        'DELIVERED',
        'FAILED',
        'BOUNCED'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE preview_type_enum AS ENUM (
        'FIRST_5',
        'RANDOM_5',
        'FAILURE_REPORT'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- 3. UPDATED_AT TRIGGER FUNCTION
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ====================================================================================
-- TABLE 1: DATA_SOURCES
-- Records external origins of participant data (CSV, Google Sheet, Google Form, Manual Form)
-- ====================================================================================
CREATE TABLE IF NOT EXISTS data_sources (
    source_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type source_type_enum NOT NULL,
    source_name VARCHAR(255) NOT NULL,
    source_reference TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ====================================================================================
-- TABLE 2: BATCHES
-- Central entity representing a certificate generation and delivery run
-- ====================================================================================
CREATE TABLE IF NOT EXISTS batches (
    batch_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES data_sources(source_id) ON DELETE SET NULL,
    template_id VARCHAR(255) NOT NULL,
    template_version VARCHAR(50) NOT NULL DEFAULT '1',
    template_storage_path TEXT,
    status batch_status_enum NOT NULL DEFAULT 'CREATED',
    created_by UUID,
    approved_by UUID,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_batches_updated_at
BEFORE UPDATE ON batches
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- ====================================================================================
-- TABLE 3: BATCH_PROGRESS
-- Atomic shared counters decoupled from the main batch row to eliminate lock contention
-- ====================================================================================
CREATE TABLE IF NOT EXISTS batch_progress (
    batch_id UUID PRIMARY KEY REFERENCES batches(batch_id) ON DELETE CASCADE,
    total_count INTEGER NOT NULL DEFAULT 0,
    generated_count INTEGER NOT NULL DEFAULT 0,
    sent_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_batch_progress_updated_at
BEFORE UPDATE ON batch_progress
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- ====================================================================================
-- TABLE 4: PARTICIPANTS
-- Immutable snapshot of imported participant data frozen at import time
-- ====================================================================================
CREATE TABLE IF NOT EXISTS participants (
    participant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id UUID NOT NULL REFERENCES batches(batch_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    participant_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_row_number INTEGER,
    validation_status validation_status_enum NOT NULL DEFAULT 'PENDING',
    validation_error TEXT,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ====================================================================================
-- TABLE 5: GENERATION_TASKS
-- Individual certificate-generation tasks enabling per-participant retry at scale
-- ====================================================================================
CREATE TABLE IF NOT EXISTS generation_tasks (
    task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id UUID NOT NULL REFERENCES batches(batch_id) ON DELETE CASCADE,
    participant_id UUID NOT NULL REFERENCES participants(participant_id) ON DELETE CASCADE,
    status task_status_enum NOT NULL DEFAULT 'PENDING',
    attempts INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_generation_task_participant UNIQUE (participant_id)
);

CREATE TRIGGER trg_generation_tasks_updated_at
BEFORE UPDATE ON generation_tasks
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- ====================================================================================
-- TABLE 6: CERTIFICATES
-- Metadata for generated certificates stored in Supabase Storage
-- ====================================================================================
CREATE TABLE IF NOT EXISTS certificates (
    certificate_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id UUID NOT NULL REFERENCES batches(batch_id) ON DELETE CASCADE,
    participant_id UUID NOT NULL REFERENCES participants(participant_id) ON DELETE CASCADE,
    generation_task_id UUID REFERENCES generation_tasks(task_id) ON DELETE SET NULL,
    template_id VARCHAR(255) NOT NULL,
    template_version VARCHAR(50) NOT NULL,
    storage_path TEXT NOT NULL,
    file_hash VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_certificate_batch_participant UNIQUE (batch_id, participant_id)
);

-- ====================================================================================
-- TABLE 7: DELIVERY_TASKS
-- Individual delivery tasks with sha256(certificate_id) idempotency key
-- ====================================================================================
CREATE TABLE IF NOT EXISTS delivery_tasks (
    delivery_task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id UUID NOT NULL REFERENCES batches(batch_id) ON DELETE CASCADE,
    certificate_id UUID NOT NULL REFERENCES certificates(certificate_id) ON DELETE CASCADE,
    provider VARCHAR(100) NOT NULL DEFAULT 'RESEND',
    status task_status_enum NOT NULL DEFAULT 'PENDING',
    attempts INTEGER NOT NULL DEFAULT 0,
    idempotency_key VARCHAR(64) NOT NULL UNIQUE,
    error TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_delivery_tasks_updated_at
BEFORE UPDATE ON delivery_tasks
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- ====================================================================================
-- TABLE 8: DELIVERIES
-- Result records for actual provider dispatches, enabling zero-log error diagnosis
-- ====================================================================================
CREATE TABLE IF NOT EXISTS deliveries (
    delivery_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    delivery_task_id UUID NOT NULL REFERENCES delivery_tasks(delivery_task_id) ON DELETE CASCADE,
    certificate_id UUID NOT NULL REFERENCES certificates(certificate_id) ON DELETE CASCADE,
    recipient VARCHAR(255) NOT NULL,
    provider VARCHAR(100) NOT NULL,
    status delivery_status_enum NOT NULL DEFAULT 'PENDING',
    provider_message_id VARCHAR(255),
    error TEXT,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ====================================================================================
-- TABLE 9: PREVIEWS
-- Stores sample certificates (first 5, random 5) and failure reports for human approval
-- ====================================================================================
CREATE TABLE IF NOT EXISTS previews (
    preview_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id UUID NOT NULL REFERENCES batches(batch_id) ON DELETE CASCADE,
    certificate_id UUID REFERENCES certificates(certificate_id) ON DELETE SET NULL,
    preview_type preview_type_enum NOT NULL,
    preview_url TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ====================================================================================
-- 4. PERFORMANCE INDEXES
-- ====================================================================================
CREATE INDEX IF NOT EXISTS idx_data_sources_type ON data_sources(source_type);
CREATE INDEX IF NOT EXISTS idx_batches_status ON batches(status);
CREATE INDEX IF NOT EXISTS idx_batches_source_id ON batches(source_id);
CREATE INDEX IF NOT EXISTS idx_participants_batch_id ON participants(batch_id);
CREATE INDEX IF NOT EXISTS idx_participants_validation_status ON participants(batch_id, validation_status);
CREATE INDEX IF NOT EXISTS idx_participants_email ON participants(email);
CREATE INDEX IF NOT EXISTS idx_generation_tasks_batch_status ON generation_tasks(batch_id, status);
CREATE INDEX IF NOT EXISTS idx_certificates_batch_id ON certificates(batch_id);
CREATE INDEX IF NOT EXISTS idx_certificates_participant_id ON certificates(participant_id);
CREATE INDEX IF NOT EXISTS idx_delivery_tasks_batch_status ON delivery_tasks(batch_id, status);
CREATE INDEX IF NOT EXISTS idx_delivery_tasks_certificate_id ON delivery_tasks(certificate_id);
CREATE INDEX IF NOT EXISTS idx_delivery_tasks_idempotency_key ON delivery_tasks(idempotency_key);
CREATE INDEX IF NOT EXISTS idx_deliveries_task_id ON deliveries(delivery_task_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_certificate_id ON deliveries(certificate_id);
CREATE INDEX IF NOT EXISTS idx_previews_batch_id ON previews(batch_id);

-- ====================================================================================
-- 5. ROW LEVEL SECURITY (RLS)
-- Enables security by default while providing service-role full access
-- ====================================================================================
ALTER TABLE data_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE batches ENABLE ROW LEVEL SECURITY;
ALTER TABLE batch_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE generation_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE certificates ENABLE ROW LEVEL SECURITY;
ALTER TABLE delivery_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE deliveries ENABLE ROW LEVEL SECURITY;
ALTER TABLE previews ENABLE ROW LEVEL SECURITY;

-- Service role bypasses RLS automatically in Supabase, but explicit policies ensure clean access
CREATE POLICY "Service role full access on data_sources" ON data_sources FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on batches" ON batches FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on batch_progress" ON batch_progress FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on participants" ON participants FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on generation_tasks" ON generation_tasks FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on certificates" ON certificates FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on delivery_tasks" ON delivery_tasks FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on deliveries" ON deliveries FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on previews" ON previews FOR ALL TO service_role USING (true) WITH CHECK (true);
