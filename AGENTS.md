# AGENTS.md

## Repository Rules For Agents — Autocert Certificate Automation

This repository contains the backend and database architecture for the Autocert Certificate Automation Module. Treat `docs/architecture-prd.md` and `docs/certificate-engine-architecture.md` as the source of truth for architecture, delivery phases, and modular engine design.

---

## Current Project Memory Checkpoint (State of Repository)

### 1. What Has Been Completed & Verified
- **Native-First Architecture (Zero Docker)**: All container files removed; 100% native execution on Python 3.12+ and Node.
- **Supabase Database Schema (9 Tables)**: Fully codified under `backend/supabase/migrations/`:
  - `data_sources` (source tracking: CSV, Google Sheets, Google Forms, Manual).
  - `batches` (FSM transitions: `CREATED` ➔ `IMPORTING` ➔ `VALIDATING` ➔ `READY_FOR_GENERATION` ➔ `GENERATING` ➔ `GENERATED` ➔ `AWAITING_APPROVAL` ➔ `SENDING` ➔ `COMPLETED` / `PARTIAL_SUCCESS` / `FAILED` / `CANCELLED`).
  - `batch_progress` (atomic counters decoupled from `batches` to eliminate lock contention).
  - `participants` (immutable snapshot frozen at import time with `participant_data JSONB`).
  - `generation_tasks` (task-level granularity for per-row retry at scale).
  - `certificates` (version-pinned templates, sha256 file hashes, storage paths).
  - `delivery_tasks` (unique `idempotency_key = sha256(certificate_id)` for zero duplicate sends).
  - `deliveries` (provider dispatch records storing message IDs and errors for zero-log troubleshooting).
  - `previews` (sample certificates & failure reports for human approval gate).
- **Supabase Storage**: Active buckets `certificates` (10MB) and `templates` (25MB) provisioned via `backend/supabase/init_storage.py`.
- **SOLID Modular Certificate Engine (`backend/app/`)**:
  - `TemplateProvider` Protocol: `LocalTemplateProvider` & `SupabaseTemplateProvider`.
  - `CertificateEngine` Protocol:
    - `PillowImageEngine`: Dynamic font auto-scaling, auto-centering, script typography.
    - `PyMuPdfEngine`: Vector PDF anchor detection (`THIS CERTIFICATE IS PRESENTED TO`) and crisp vector text insertion.
    - `DocxTemplateEngine`: Word DOCX templates using `docxtpl` with Jinja2 tags.
  - `CertificateEngineFactory`: Dynamically resolves engines by template extension.
  - `TextFittingService`: Measures bounding boxes, dynamically downsizes font for long names, eliminates random X/Y coordinates.
  - `StorageSink` Protocol: `LocalDiskSink` (folder-out to `sample_templates/output/`) & `SupabaseStorageSink`.
  - `CertificatePipeline`: Dependency-injected batch orchestrator.
- **Test Assets & Mock Data**:
  - `backend/sample_templates/`: Real templates (`Black Gold Formal Appreciation Certificate.png` and `.pdf`).
  - `backend/sample_data/mock_participants.json`: 5-member dataset with diverse name lengths and special characters.
  - `backend/run_generation_test.py`: Standalone test runner supporting `--mode local` and `--mode cloud`.
- **Dependencies**: Pinned exact versions in `backend/requirements.txt`.

### 2. Next Action on Standby
- Await the user's explicit instruction to execute the certificate generation test (`backend/run_generation_test.py`).

---

## Mandatory Execution & Git Workflow Rules

1. **Initialize Python Virtual Environment First**:
   - Always initialize and verify the Python virtual environment (`.venv` in `backend/`) before executing scripts or running backend commands.
   - Activate `.venv` explicitly prior to running any backend process:
     ```powershell
     cd backend
     if (!(Test-Path .venv)) { python -m venv .venv }
     .venv\Scripts\Activate.ps1
     ```

2. **Install Modules from `requirements.txt` Strictly Inside Active `.venv`**:
   - Never install packages into the global Python environment.
   - Install dependencies using:
     ```powershell
     pip install -r requirements.txt
     ```
   - Always keep `backend/requirements.txt` updated with pinned versions when adding new libraries.

3. **Compile & Validate Properly**:
   - Before completing tasks, always compile and validate code properly:
     ```powershell
     .venv\Scripts\python -m compileall backend
     ```
   - Ensure all SQL files are syntactically valid PostgreSQL statements.

4. **Commit and Push Whenever Required**:
   - Create atomic, descriptive git commits whenever a milestone, feature, or requested change is completed.
   - Push commits to `origin/main` to keep progress synchronized and safe.

5. **Environment & Security Protection**:
   - `backend/.env` contains sensitive live Supabase credentials. It **must never be modified or deleted**.
   - Always maintain `backend/.env.example` when introducing new configuration keys (e.g. CORS, ports, external service keys).

---

## Coding Principles

- **SOLID & DRY**: Composable, small services; single responsibility per module.
- **Dependency Inversion**: High-level modules depend on abstractions (`TemplateProvider`, `CertificateEngine`, `StorageSink`), not concrete implementations.
- **Decoupled Architecture**: Do not make the frontend and backend depend on each other's internal structure.