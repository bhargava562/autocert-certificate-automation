# Claude Instructions — Autocert Certificate Automation

## Current Project Memory Checkpoint

Autocert is a plug-in certificate automation module built for an external parent dashboard. The current state is fully native (zero Docker), backed by Python 3.12+ and Supabase.

### 1. Current State of Repository
- **Database Architecture (9 Core Tables)**: Codified in `backend/supabase/migrations/`:
  - `data_sources`, `batches`, `batch_progress`, `participants`, `generation_tasks`, `certificates`, `delivery_tasks`, `deliveries`, `previews`.
- **Supabase Storage**: Active buckets `certificates` (10MB) and `templates` (25MB) provisioned and verified.
- **SOLID Modular Certificate Engine (`backend/app/`)**:
  - `TemplateProvider` Protocol (`LocalTemplateProvider`, `SupabaseTemplateProvider`).
  - `CertificateEngine` Protocol (`PillowImageEngine`, `PyMuPdfEngine`, `DocxTemplateEngine`).
  - `CertificateEngineFactory` (resolves engine dynamically by file extension).
  - `TextFittingService` (dynamic auto-scaling, horizontal centering, word wrapping — eliminates random X/Y coordinates).
  - `StorageSink` Protocol (`LocalDiskSink`, `SupabaseStorageSink`).
  - `CertificatePipeline` (Dependency-injected orchestrator).
- **Execution Modes**:
  - **Local Mode**: Reads from `backend/sample_templates/` and outputs directly to `backend/sample_templates/output/`.
  - **Cloud Mode**: Reads from Supabase `templates` bucket and uploads to `certificates` bucket with signed URLs.
- **Mock Dataset**: 5 diverse participants in `backend/sample_data/mock_participants.json`.
- **Dependencies**: Pinned exact versions in `backend/requirements.txt`.
- **Standby State**: Awaiting user instruction to execute the test runner (`backend/run_generation_test.py`).

---

## Domain Architecture Flow

```text
Data Source ➔ Batch ➔ Participant Snapshot ➔ Generation Task ➔ Certificate ➔ Delivery Task ➔ Delivery
                     ├── Batch Progress (Decoupled Atomic Counters)
                     └── Preview (Human Approval Gate Evidence: First 5, Random 5, Failure Report)
```

---

## Mandatory Execution & Git Workflow Rules

1. **Initialize Python Virtual Environment**:
   - Always initialize and activate `.venv` inside `backend/` before running any scripts:
     ```powershell
     cd backend
     if (!(Test-Path .venv)) { python -m venv .venv }
     .venv\Scripts\Activate.ps1
     ```

2. **Install Modules from `requirements.txt` Inside Active `.venv`**:
   - Never install packages into the global environment:
     ```powershell
     pip install -r requirements.txt
     ```

3. **Compile & Validate Properly**:
   - Always compile and validate code before declaring work complete:
     ```powershell
     .venv\Scripts\python -m compileall backend
     ```
   - Ensure zero syntax, import, or type errors.

4. **Commit and Push Whenever Required**:
   - Commit code with atomic, descriptive messages (`feat(...)`, `fix(...)`, `docs(...)`).
   - Push commits to `origin/main` to keep progress durable and synchronized.

5. **Protect Sensitive Credentials**:
   - `backend/.env` contains live Supabase credentials. **It must never be modified or deleted.**
   - Maintain `backend/.env.example` when adding new configuration options.

---

## Technical Guardrails

- **Zero Docker**: Run natively on host Windows environment.
- **SOLID Design**: All certificate generators implement `CertificateEngine` protocol; orchestrator depends on abstractions, not concrete engines.
- **Dynamic Mapping**: Never use random/arbitrary coordinates. Use normalized percentages, dynamic font downscaling, and text bounding box calculations.