-- ====================================================================================
-- Seed File: backend/supabase/seed.sql
-- Description: Demonstrates end-to-end data pipeline across all 9 tables:
--   - 1 data source (Google Sheet)
--   - 1 batch (status: AWAITING_APPROVAL)
--   - 1 batch_progress row (5 total, 5 generated, 0 sent, 0 failed)
--   - 5 participants (4 valid, 1 invalid to test failure reporting)
--   - 4 completed generation tasks, 1 failed validation task
--   - 4 generated certificates
--   - 4 delivery tasks with sha256 idempotency keys
--   - 2 preview records (FIRST_5 sample + FAILURE_REPORT)
-- ====================================================================================

DO $$
DECLARE
    v_source_id UUID := '11111111-1111-1111-1111-111111111111';
    v_batch_id UUID := '22222222-2222-2222-2222-222222222222';
    
    v_part1_id UUID := '33333333-1111-1111-1111-111111111111';
    v_part2_id UUID := '33333333-2222-2222-2222-222222222222';
    v_part3_id UUID := '33333333-3333-3333-3333-333333333333';
    v_part4_id UUID := '33333333-4444-4444-4444-444444444444';
    v_part5_id UUID := '33333333-5555-5555-5555-555555555555';
    
    v_gtask1_id UUID := '44444444-1111-1111-1111-111111111111';
    v_gtask2_id UUID := '44444444-2222-2222-2222-222222222222';
    v_gtask3_id UUID := '44444444-3333-3333-3333-333333333333';
    v_gtask4_id UUID := '44444444-4444-4444-4444-444444444444';
    
    v_cert1_id UUID := '55555555-1111-1111-1111-111111111111';
    v_cert2_id UUID := '55555555-2222-2222-2222-222222222222';
    v_cert3_id UUID := '55555555-3333-3333-3333-333333333333';
    v_cert4_id UUID := '55555555-4444-4444-4444-444444444444';
BEGIN
    -- 1. Insert Data Source
    INSERT INTO data_sources (source_id, source_type, source_name, source_reference, metadata)
    VALUES (
        v_source_id,
        'GOOGLE_SHEET',
        'National AI Hackathon 2026 Participants',
        'https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit',
        '{"sheet_name": "FinalRegistrations", "total_rows": 5}'::jsonb
    ) ON CONFLICT (source_id) DO NOTHING;

    -- 2. Insert Batch
    INSERT INTO batches (batch_id, source_id, template_id, template_version, template_storage_path, status)
    VALUES (
        v_batch_id,
        v_source_id,
        'tpl_hackathon_winner_v2',
        '2',
        'templates/tpl_hackathon_winner_v2.pdf',
        'AWAITING_APPROVAL'
    ) ON CONFLICT (batch_id) DO NOTHING;

    -- 3. Insert Batch Progress
    INSERT INTO batch_progress (batch_id, total_count, generated_count, sent_count, failed_count)
    VALUES (
        v_batch_id,
        5,
        4,
        0,
        1
    ) ON CONFLICT (batch_id) DO UPDATE SET
        total_count = EXCLUDED.total_count,
        generated_count = EXCLUDED.generated_count,
        sent_count = EXCLUDED.sent_count,
        failed_count = EXCLUDED.failed_count;

    -- 4. Insert Participants (4 Valid, 1 Invalid)
    INSERT INTO participants (participant_id, batch_id, name, email, participant_data, source_row_number, validation_status, validation_error)
    VALUES
    (v_part1_id, v_batch_id, 'Alice Johnson', 'alice.j@example.com', '{"college": "MIT", "track": "AI", "rank": 1}'::jsonb, 2, 'VALID', NULL),
    (v_part2_id, v_batch_id, 'Bob Smith', 'bob.s@example.com', '{"college": "Stanford", "track": "AI", "rank": 2}'::jsonb, 3, 'VALID', NULL),
    (v_part3_id, v_batch_id, 'Carol White', 'carol.w@example.com', '{"college": "Berkeley", "track": "Web3", "rank": 3}'::jsonb, 4, 'VALID', NULL),
    (v_part4_id, v_batch_id, 'David Brown', 'david.b@example.com', '{"college": "CMU", "track": "Cloud", "rank": 4}'::jsonb, 5, 'VALID', NULL),
    (v_part5_id, v_batch_id, 'Eva Green', NULL, '{"college": "Oxford", "track": "Design"}'::jsonb, 6, 'INVALID', 'Missing required email address')
    ON CONFLICT (participant_id) DO NOTHING;

    -- 5. Insert Generation Tasks (4 Completed)
    INSERT INTO generation_tasks (task_id, batch_id, participant_id, status, attempts, started_at, completed_at)
    VALUES
    (v_gtask1_id, v_batch_id, v_part1_id, 'COMPLETED', 1, now() - interval '2 minutes', now() - interval '1 minute 50 seconds'),
    (v_gtask2_id, v_batch_id, v_part2_id, 'COMPLETED', 1, now() - interval '1 minute 50 seconds', now() - interval '1 minute 40 seconds'),
    (v_gtask3_id, v_batch_id, v_part3_id, 'COMPLETED', 1, now() - interval '1 minute 40 seconds', now() - interval '1 minute 30 seconds'),
    (v_gtask4_id, v_batch_id, v_part4_id, 'COMPLETED', 1, now() - interval '1 minute 30 seconds', now() - interval '1 minute 20 seconds')
    ON CONFLICT (participant_id) DO NOTHING;

    -- 6. Insert Generated Certificates
    INSERT INTO certificates (certificate_id, batch_id, participant_id, generation_task_id, template_id, template_version, storage_path, file_hash)
    VALUES
    (v_cert1_id, v_batch_id, v_part1_id, v_gtask1_id, 'tpl_hackathon_winner_v2', '2', 'certificates/batch_22222222/cert_alice.pdf', encode(sha256('alice'::bytea), 'hex')),
    (v_cert2_id, v_batch_id, v_part2_id, v_gtask2_id, 'tpl_hackathon_winner_v2', '2', 'certificates/batch_22222222/cert_bob.pdf', encode(sha256('bob'::bytea), 'hex')),
    (v_cert3_id, v_batch_id, v_part3_id, v_gtask3_id, 'tpl_hackathon_winner_v2', '2', 'certificates/batch_22222222/cert_carol.pdf', encode(sha256('carol'::bytea), 'hex')),
    (v_cert4_id, v_batch_id, v_part4_id, v_gtask4_id, 'tpl_hackathon_winner_v2', '2', 'certificates/batch_22222222/cert_david.pdf', encode(sha256('david'::bytea), 'hex'))
    ON CONFLICT (batch_id, participant_id) DO NOTHING;

    -- 7. Insert Delivery Tasks (Ready to send after approval, idempotency_key = sha256(certificate_id))
    INSERT INTO delivery_tasks (delivery_task_id, batch_id, certificate_id, provider, status, idempotency_key)
    VALUES
    ('66666666-1111-1111-1111-111111111111', v_batch_id, v_cert1_id, 'RESEND', 'PENDING', encode(sha256(v_cert1_id::text::bytea), 'hex')),
    ('66666666-2222-2222-2222-222222222222', v_batch_id, v_cert2_id, 'RESEND', 'PENDING', encode(sha256(v_cert2_id::text::bytea), 'hex')),
    ('66666666-3333-3333-3333-333333333333', v_batch_id, v_cert3_id, 'RESEND', 'PENDING', encode(sha256(v_cert3_id::text::bytea), 'hex')),
    ('66666666-4444-4444-4444-444444444444', v_batch_id, v_cert4_id, 'RESEND', 'PENDING', encode(sha256(v_cert4_id::text::bytea), 'hex'))
    ON CONFLICT (idempotency_key) DO NOTHING;

    -- 8. Insert Previews for Human Approval Gate
    INSERT INTO previews (preview_id, batch_id, certificate_id, preview_type, preview_url)
    VALUES
    ('77777777-1111-1111-1111-111111111111', v_batch_id, v_cert1_id, 'FIRST_5', 'https://vxfxbiojolsqoosvcheh.supabase.co/storage/v1/object/public/previews/sample_alice.png'),
    ('77777777-2222-2222-2222-222222222222', v_batch_id, NULL, 'FAILURE_REPORT', 'https://vxfxbiojolsqoosvcheh.supabase.co/storage/v1/object/public/previews/validation_report.json')
    ON CONFLICT (preview_id) DO NOTHING;

END $$;
