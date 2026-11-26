# AGENTS.md

## Repository Rules For Agents — Autocert Certificate Automation

This repository contains the full-stack architecture for the **Autocert Certificate Automation Module** (FastAPI backend, React + Vite frontend, and Supabase PostgreSQL + Storage). Treat `docs/architecture-prd.md` and `docs/certificate-engine-architecture.md` as the source of truth for domain requirements, delivery phases, and modular engine design.

---

## System Architecture

### 1. Native-First Stack (Zero Docker)
- **Backend:** Python 3.12+ (`.venv` in `backend/`), FastAPI (`backend/app/main.py`), Uvicorn, Pillow, PyMuPDF (`pymupdf` / `fitz`), `openpyxl`, `xlrd`, `docxtpl`, `Jinja2`, `psycopg` v3.
- **Frontend:** React 19 + Vite 8 (`frontend/`), `lucide-react`, `papaparse`, `xlsx`, `oxlint`. Vite proxies `/api` to `http://127.0.0.1:8000` in development (`frontend/vite.config.js`), and supports `VITE_API_URL` for direct cross-origin requests.
- **Database & Storage:** Supabase PostgreSQL (9-table ERD) and Supabase Storage (`certificates` 10MB, `templates` 25MB) under `backend/supabase/`.

### 2. Backend Module Layout (`backend/app/`)
- `core/config.py`: Immutable `Settings` dataclass loaded via `load_settings()` from `backend/.env` (with `os.getenv` fallback). Parses Supabase credentials, `HOST`, `PORT`, `ENVIRONMENT`, `CORS_ORIGINS`, and SMTP settings without modifying `backend/.env`.
- `main.py`: FastAPI application (`1.1.0`), `CORSMiddleware` configured from `Settings.cors_origins`, and REST endpoints:
  - `GET /`, `GET /api/health` — Service & SMTP readiness check.
  - `POST /api/dataset/parse` — Server-side spreadsheet/JSON parsing via `dataset_parser.load_dataset`.
  - `POST /api/certificates/generate` (alias `/certificate/batches/generate`) — Concurrent batch rendering + optional paced SMTP dispatch.
  - `POST /api/certificates/send-batch-emails` & `POST /api/certificates/send-single-email` — Batch and 1-to-1 email dispatch using Jinja2 HTML (`backend/sample_templates/sample_email_template.html`).
  - `POST /api/certificates/test-smtp` — Live SMTP STARTTLS connectivity & auth check.
  - `GET /api/certificates/download/{filename}` — Serves generated PNG/PDF files from `backend/sample_templates/output/`.
- `services/models.py`: Domain dataclasses (`FieldConfig`, `TemplateManifest`, `RenderResult`).
- `services/protocols.py`: SOLID protocol interfaces (`TemplateProvider`, `CertificateEngine`, `StorageSink`) for dependency inversion.
- `services/pipeline.py`: `CertificatePipeline` orchestrating `TemplateProvider`, `CertificateEngineFactory`, and `StorageSink` (`generate_one`, `generate_batch`).
- `services/template_scanner.py`: `scan_template_placeholders()` scans uploaded PDF or image templates via PyMuPDF for placeholder tokens (`{{name}}`, `{{year}}`, `{{dept}}`, `{{title}}`, etc.) to synthesize proportional `FieldConfig` bounding boxes; falls back to calibrated layout manifests when no tokens are found.
- `services/dataset_parser.py`: Unified ingestion (`load_dataset()`) for `.xlsx`/`.xlsm`/`.xltx` (`openpyxl`), `.xls` (`xlrd`), `.csv`/`.tsv` (`csv.Sniffer`), and `.json`, with cell coercion and header sanitization.
- `services/text_fitting.py`: `TextFittingService` resolves fonts (custom `assets/fonts` -> `C:\Windows\Fonts` -> fallback), caches `ImageFont` instances, and performs adaptive-step auto-scaling (`step = max(1, int(target_size * 0.025))`) and word wrapping.
- `services/engines/`:
  - `factory.py`: `CertificateEngineFactory` (Open/Closed engine registry).
  - `image_engine.py`: `PillowImageEngine` renders onto raster images with `clear_area` wiping, single-line auto-fitting, multi-line wrapping fallback, and PNG/PDF output.
  - `pdf_engine.py`: `PyMuPdfEngine` redacts `clear_area` & `{{...}}` tags on vector PDFs and injects auto-downscaled text via `insert_textbox`.
  - `docx_engine.py`: `DocxTemplateEngine` for `.docx` templates.
- `services/providers/`: `local_provider.py` and `supabase_provider.py` implementing `TemplateProvider` / `StorageSink`.

### 3. Frontend Architecture (`frontend/src/`)
- `pages/Home.jsx` & `App.jsx`: Operational dashboard with live `/api/health` polling, metric cards, collapsible 3-step workflow, and split-view inspection.
- `hooks/useCertificateGeneration.js`: Central workflow state, synonym-based column auto-matching (`SYSTEM_FIELDS`), batch payload assembly, generation progress, and single-email resend handling.
- `services/certificateApi.js`: Fetch client for `/api/health`, `/api/certificates/generate`, `/api/certificates/send-single-email`, `/api/certificates/test-smtp`, and `/api/certificates/download/{filename}`.
- `components/`: `Header`, `EmptyState`, `UploadTemplate`, `UploadData` (client-side parsing via `papaparse` & `xlsx`), `DataMapping` (column mapping + output format PNG/PDF + bulk email toggle/subject), `ValidationSummary`, `GenerateButton`, `GenerationProgress`, `CertificateList`, and `CertificatePreview` (PNG/PDF preview, fullscreen zoom, download, 1-click email).

### 4. Supabase Database & Storage (`backend/supabase/`)
- **9 Core Tables** (`backend/supabase/migrations/20260907000001_initial_erd_schema.sql`):
  - `data_sources`, `batches` (FSM: `CREATED` ➔ `IMPORTING` ➔ `VALIDATING` ➔ `READY_FOR_GENERATION` ➔ `GENERATING` ➔ `GENERATED` ➔ `AWAITING_APPROVAL` ➔ `SENDING` ➔ `COMPLETED` / `PARTIAL_SUCCESS` / `FAILED` / `CANCELLED`), `batch_progress` (atomic counters), `participants` (immutable `JSONB` snapshot), `generation_tasks`, `certificates`, `delivery_tasks` (`idempotency_key = sha256(certificate_id)`), `deliveries`, `previews`.
- **Storage Buckets** (`20260907000002_storage_setup.sql`, `init_storage.py`): `certificates` (10MB) and `templates` (25MB).

---

## End-to-End Code Flow

1. **Asset & Dataset Ingestion (Frontend):**
   - User uploads a template (`.png`, `.jpg`, `.jpeg`, `.pdf`) in `UploadTemplate` and a dataset (`.xlsx`, `.xls`, `.csv`, `.json`) in `UploadData`.
   - `UploadData` parses rows client-side (`xlsx` / `papaparse` / `JSON.parse`) and passes `{ file, fileName, records, columns }` to `handleDataLoaded`.
   - `useCertificateGeneration` auto-maps dataset columns against `SYSTEM_FIELDS` synonyms (`full_name`, `email`, `year`, `department`, `achievement_title`, `achievement_text`).
   - `ValidationSummary` checks required fields (`full_name`, and `email` if bulk email is enabled) before enabling `GenerateButton`.
2. **Batch Generation Request (Frontend ➔ Backend):**
   - `handleGenerate` builds normalized participant objects (auto-assigning `CERT-0001`, `CERT-0002`, ...) and posts `FormData` (`template`, `participants`, `format`, `send_emails`, `email_subject`) to `POST /api/certificates/generate`.
3. **Template Normalization & Placeholder Scanning (Backend):**
   - If the uploaded template is `.pdf`, `convert_pdf_to_image_bytes()` rasterizes page 0 at 200 DPI and redacts `{{...}}` tags.
   - `scan_template_placeholders()` inspects the template for placeholder tokens and constructs a proportional `TemplateManifest` (or falls back to calibrated defaults).
   - `normalize_record()` extracts display/delivery fields and isolates unrelated PII from rendering.
4. **Concurrent Rendering (Backend):**
   - `OUTPUT_DIR` (`backend/sample_templates/output/`) is cleared of stale files.
   - `ThreadPoolExecutor(max_workers=min(16, (os.cpu_count() or 1) + 4))` runs `render_single_certificate()` via `PillowImageEngine.render()`, writing each PNG or PDF to `OUTPUT_DIR`.
5. **Optional Paced Email Dispatch & Inspection:**
   - If `send_emails=True`, `main.py` opens a single SMTP STARTTLS session, renders `sample_email_template.html` via Jinja2 per recipient, attaches the generated certificate, and sleeps `0.15s` between sends with per-recipient error isolation.
   - Frontend displays `CertificateList` and `CertificatePreview`, fetching previews/downloads from `GET /api/certificates/download/{filename}` and supporting 1-click resends via `POST /api/certificates/send-single-email`.

---

## Key Architectural Approaches

- **Resolution-Independent Proportional Coordinates:** All `FieldConfig` positions (`x_pct`, `y_pct`), widths (`max_w_pct`), and font sizes (`font_size_pct`, `min_font_size_pct`) are normalized `[0.0, 1.0]` ratios relative to dynamic canvas dimensions, with adaptive step downscaling and multi-line wrapping fallback.
- **Defensive Area Clearing:** `clear_area` + `clear_bg_color` (and PyMuPDF redactions for `{{...}}` tags) wipe template placeholder regions prior to rendering to prevent text ghosting.
- **Decoupled Output Modes:** Each batch run targets a single output format (`png` or `pdf`) and cleans `OUTPUT_DIR` beforehand to avoid mixed artifacts.
- **SOLID & Dependency Inversion:** Core services depend on `TemplateProvider`, `CertificateEngine`, and `StorageSink` protocols rather than concrete filesystem, Pillow, PyMuPDF, or Supabase implementations.
- **Environment-Driven Configuration:** All secrets, SMTP settings, and `CORS_ORIGINS` are loaded from `backend/.env` via `app/core/config.py`.

---

## Current Project Memory Checkpoint (State of Repository)

- **CORS & Config:** `backend/app/core/config.py` and `backend/app/main.py` load `CORS_ORIGINS` from `backend/.env` (falling back to local dev origins from `backend/.env.example`), with `allow_credentials` disabled automatically if `"*"` is present.
- **Environments & Dependencies:** `backend/.venv` is configured for Python 3.15 (`C:\Python315\python.exe`) with pinned dependencies in `backend/requirements.txt` (`pydantic==2.14.4`, `pydantic_core==2.50.5`, `psycopg==3.3.9`, `psycopg-binary==3.3.9` for `cp315-win_amd64` wheel support). `frontend/node_modules` is installed and `npm run lint` (`oxlint`) passes with 0 errors.
- **Git State:** `main` is synchronized with `origin/main`; stale `origin/automatic` branch has been removed.

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
