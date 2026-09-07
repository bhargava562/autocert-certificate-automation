# GitHub Copilot Instructions — Autocert Certificate Automation

## Current Project Memory Checkpoint

Autocert is an isolated certificate automation module designed to plug into an external parent dashboard. The project runs **natively** (zero Docker) on Python 3.12+ and Supabase (PostgreSQL & Storage).

### 1. Where the Project Is Right Now (Checkpoint)
- **Database & Storage Layer**:
  - All 9 core ERD tables are codified in `backend/supabase/migrations/20260907000001_initial_erd_schema.sql` (`data_sources`, `batches`, `batch_progress`, `participants`, `generation_tasks`, `certificates`, `delivery_tasks`, `deliveries`, `previews`).
  - Storage setup in `backend/supabase/migrations/20260907000002_storage_setup.sql`.
  - Storage buckets `certificates` (10MB limit) and `templates` (25MB limit) have been provisioned and are active on Supabase.
  - Migration runners: `backend/supabase/migrate.py` (Python) and `backend/supabase/migrate.js` (Node.js).
- **SOLID Modular Certificate Generation Engine (`backend/app/`)**:
  - `TemplateProvider` protocol with `LocalTemplateProvider` (folder-in) and `SupabaseTemplateProvider` (cloud storage).
  - `CertificateEngine` protocol with:
    - `PillowImageEngine`: Raster rendering with dynamic auto-scaling, horizontal centering, and script fonts.
    - `PyMuPdfEngine`: Vector PDF search (`THIS CERTIFICATE IS PRESENTED TO`), dynamic bounding box, and vector text insertion.
    - `DocxTemplateEngine`: Word DOCX templates with Jinja2 tags via `docxtpl`.
  - `CertificateEngineFactory`: Resolves engines by file extension (`.png`, `.pdf`, `.docx`).
  - `TextFittingService`: Measures bounding boxes, dynamically downsizes fonts for long names (no random X/Y), and computes true center.
  - `StorageSink` protocol with `LocalDiskSink` (folder-out to `sample_templates/output/`) and `SupabaseStorageSink`.
  - `CertificatePipeline`: Orchestrator coordinating generation via Dependency Injection.
- **Test Assets & Mock Data**:
  - Real template in `backend/sample_templates/`: `Black Gold Formal Appreciation Certificate.png` and `.pdf`.
  - 5-member mock dataset in `backend/sample_data/mock_participants.json` (including standard, long, and hyphenated names).
  - Test runner: `backend/run_generation_test.py` (`--mode local` and `--mode cloud`).
- **Dependencies**:
  - Pinned exact versions in `backend/requirements.txt`.
- **Next Action on Standby**:
  - Awaiting user instruction to trigger the generation test.

---

## Architecture & Domain Flow

```text
Data Source ➔ Batch ➔ Participant Snapshot ➔ Generation Task ➔ Certificate ➔ Delivery Task ➔ Delivery
                     ├── Batch Progress (Decoupled Atomic Counters)
                     └── Preview (Human Approval Gate Evidence: First 5, Random 5, Failure Report)
```

### Core Design Rules
1. **Immutable Snapshot**: Participant data is frozen into `participants` at import time with `participant_data JSONB`. External sheets/forms are never accessed again during generation.
2. **Task-Level Granularity**: `generation_tasks` and `delivery_tasks` are the units of retry at 50k scale (never regenerate the whole batch).
3. **Idempotency by Design**: `delivery_tasks.idempotency_key = sha256(certificate_id)` with a unique constraint prevents duplicate emails on crash/restart.
4. **Decoupled Progress**: `batch_progress` separates `generated_count`, `sent_count`, `failed_count` from `batches` to eliminate row-lock contention.

---

## Mandatory Execution & Git Workflow Rules

### 1. Initialize Python Virtual Environment & Install Modules
- Always initialize and verify the Python virtual environment (`backend/.venv`) before running anything.
- **Install dependencies from `requirements.txt` strictly inside the activated `.venv`**:
  ```powershell
  cd backend
  if (!(Test-Path .venv)) { python -m venv .venv }
  .venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  ```
- Never install packages into the global Python environment.

### 2. Native-First Workflow (Zero Docker)
- All runtime checks, tests, and scripts must execute natively on the host. Do not introduce Docker or container wrappers.

### 3. Environment & Security Protection
- `backend/.env` contains live Supabase credentials. **It must never be modified or deleted.**
- Document new environment variables in `backend/.env.example`.

### 4. Compilation & Validation
- Before declaring a task or milestone complete, always validate code:
  ```powershell
  .venv\Scripts\python -m compileall backend
  ```
- Ensure zero compilation errors and valid PostgreSQL syntax.

### 5. Git Commit and Push Discipline
- Commit code with atomic, descriptive messages (`feat(...)`, `fix(...)`, `docs(...)`).
- Push to remote `origin/main` to keep progress safely synchronized:
  ```powershell
  git add -A
  git commit -m "feat(...): ..."
  git push origin main
  ```
