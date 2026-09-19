-- ====================================================================================
-- Migration: 20260907000002_storage_setup.sql
-- Description: Sets up Supabase Storage buckets for certificates and templates,
-- with secure RLS policies for uploads and signed URL downloads.
-- ====================================================================================

-- 1. INSERT STORAGE BUCKETS
-- Insert 'certificates' bucket (private, downloaded via signed URLs)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'certificates',
    'certificates',
    false,
    10485760, -- 10MB limit per certificate file
    ARRAY['application/pdf', 'image/png', 'image/jpeg', 'image/webp']
)
ON CONFLICT (id) DO UPDATE SET
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

-- Insert 'templates' bucket (private, downloaded by certificate generator engine)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'templates',
    'templates',
    false,
    26214400, -- 25MB limit per template file
    ARRAY['application/pdf', 'image/png', 'image/svg+xml', 'application/json']
)
ON CONFLICT (id) DO UPDATE SET
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

-- 2. STORAGE POLICIES
-- Service role has full unrestricted access to both buckets
CREATE POLICY "Service role full access on certificates bucket"
ON storage.objects FOR ALL TO service_role
USING (bucket_id = 'certificates')
WITH CHECK (bucket_id = 'certificates');

CREATE POLICY "Service role full access on templates bucket"
ON storage.objects FOR ALL TO service_role
USING (bucket_id = 'templates')
WITH CHECK (bucket_id = 'templates');
