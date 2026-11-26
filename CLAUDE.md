# Claude Instructions — Autocert Certificate Automation

## Overview & Stack

Autocert is a native-first (zero Docker) certificate automation module built for external dashboard integration:
- **Backend:** FastAPI + Uvicorn (`backend/app/main.py`), Python 3.12+ (`.venv`), Pillow, PyMuPDF (`fitz`), `openpyxl`, `xlrd`, `docxtpl`, `Jinja2`, `psycopg` v3.
- **Frontend:** React 19 + Vite 8 (`frontend/`), `lucide-react`, `papaparse`, `xlsx`, `oxlint`. Vite proxies `/api` to `http://127.0.0.1:8000` (`frontend/vite.config.js`).
- **Database & Storage:** Supabase PostgreSQL (9-table ERD) and Supabase Storage (`certificates` 10MB, `templates` 25MB) under `backend/supabase/`.

---

## Architecture & Module Map

### Backend (`backend/app/`)
- `core/config.py`: `Settings` dataclass & `load_settings()` reading `backend/.env` (with `os.getenv` fallback) for Supabase, `HOST`, `PORT`, `ENVIRONMENT`, `CORS_ORIGINS`, and SMTP credentials.
- `main.py`: FastAPI app with env-driven `CORSMiddleware` and endpoints:
  - `GET /`, `GET /api/health`
  - `POST /api/dataset/parse`
  - `POST /api/certificates/generate` (alias `/certificate/batches/generate`)
  - `POST /api/certificates/send-batch-emails`, `POST /api/certificates/send-single-email`
  - `POST /api/certificates/test-smtp`
  - `GET /api/certificates/download/{filename}`
- `services/models.py`: `FieldConfig`, `TemplateManifest`, `RenderResult`.
- `services/protocols.py`: `TemplateProvider`, `CertificateEngine`, `StorageSink` protocols.
- `services/pipeline.py`: `CertificatePipeline` orchestrator (`generate_one`, `generate_batch`).
- `services/template_scanner.py`: `scan_template_placeholders()` locates `{{name}}`, `{{year}}`, `{{dept}}`, `{{title}}`, etc. via PyMuPDF and generates proportional `FieldConfig` manifests (with calibrated fallback).
- `services/dataset_parser.py`: `load_dataset()` unified parser for `.xlsx`/`.xlsm`/`.xltx`, `.xls`, `.csv`/`.tsv`, and `.json`.
- `services/text_fitting.py`: `TextFittingService` font resolution, caching, adaptive-step downscaling, and word wrapping.
- `services/engines/`: `CertificateEngineFactory` (`factory.py`), `PillowImageEngine` (`image_engine.py`), `PyMuPdfEngine` (`pdf_engine.py`), `DocxTemplateEngine` (`docx_engine.py`).
- `services/providers/`: `local_provider.py`, `supabase_provider.py`.

### Frontend (`frontend/src/`)
- `pages/Home.jsx` & `App.jsx`: Operations dashboard, `/api/health` polling, 3-step workflow, and split-view inspection.
- `hooks/useCertificateGeneration.js`: State management, `SYSTEM_FIELDS` synonym auto-mapping, validation, batch generation, and single-email resends.
- `services/certificateApi.js`: API client wrapping `/api/*` endpoints.
- `components/`: `Header`, `EmptyState`, `UploadTemplate`, `UploadData`, `DataMapping`, `ValidationSummary`, `GenerateButton`, `GenerationProgress`, `CertificateList`, `CertificatePreview`.

---

## End-to-End Code Flow

```text
[Frontend: UploadTemplate + UploadData (xlsx/papaparse/JSON)]
        │
        ▼  (Synonym auto-mapping + ValidationSummary)
[useCertificateGeneration.handleGenerate()]
        │  POST /api/certificates/generate (FormData)
        ▼
[FastAPI main.py]
  ├─► PDF template? -> convert_pdf_to_image_bytes() (PyMuPDF 200 DPI + {{tag}} redaction)
  ├─► scan_template_placeholders() -> proportional TemplateManifest
  ├─► normalize_record() -> isolates PII from rendering fields
  ├─► Clean OUTPUT_DIR -> ThreadPoolExecutor -> PillowImageEngine.render() (PNG or PDF)
  └─► Optional send_emails -> single SMTP STARTTLS session, Jinja2 HTML, 0.15s pacing
        │
        ▼
[Frontend: CertificateList + CertificatePreview]
  ├─► GET /api/certificates/download/{filename}
  └─► POST /api/certificates/send-single-email
```

### Target Supabase Domain Flow (`backend/supabase/migrations/`)
```text
Data Source ➔ Batch (FSM) ➔ Participant Snapshot (JSONB) ➔ Generation Task ➔ Certificate ➔ Delivery Task (sha256 idempotency) ➔ Delivery
                           ├── Batch Progress (Decoupled Atomic Counters)
                           └── Preview (Human Approval Gate Evidence)
```

---

## Key Approaches & Design Guardrails

- **Proportional Coordinates & Overflow Policy:** All `FieldConfig` positions (`x_pct`, `y_pct`), widths (`max_w_pct`), heights (`max_h_pct`, `max_lines`), alignments (`align`, `v_align`), and font sizes (`font_size_pct`, `min_font_size_pct`) are normalized `0.0–1.0` ratios. `overflow_policy` (`shrink_wrap|ellipsize|flag_overflow`) prevents silent text bleed, and `RenderResult` surfaces `overflowed` + `warnings` to the UI.
- **Vector PDF vs. Raster Separation:** `.pdf` templates targeting `pdf` output render natively via `PyMuPdfEngine` (redacting `{{...}}` tags and using explicit `clear_bg_color` only when non-transparent); raster templates / PNG output use `PillowImageEngine`.
- **Batch-Scoped Artifacts & Idempotency:** Outputs are written to `backend/sample_templates/output/{batch_id}/{certificate_id}.{ext}` (never wiping `OUTPUT_DIR`), and batch email dispatch deduplicates using `sha256(certificate_id)`.
- **SOLID & Dependency Inversion:** Engines implement `CertificateEngine`; pipeline depends on protocols (`TemplateProvider`, `CertificateEngine`, `StorageSink`).
- **Env-Driven Config & CORS:** `backend/app/core/config.py` loads `CORS_ORIGINS`, `DEFAULT_MIN_FONT_SIZE_PCT`, `DEFAULT_MAX_LINES`, and `SMTP_TIMEOUT_SECONDS` from `backend/.env` with defaults in `backend/.env.example`.

## Current Checkpoint
- **Backend & Frontend Hardened:** Text-fitting bounds, vector PDF decoupling, batch-scoped output paths, `sha256` email idempotency, and frontend overflow/warning badges + post-review batch email support are implemented on `main`.
- **Environment:** `backend/.venv` uses Python 3.15 (`pydantic==2.14.4`, `pydantic_core==2.50.5`, `psycopg==3.3.9`, `psycopg-binary==3.3.9`); `frontend` passes `oxlint` and `vite build`. (Note: Windows Application Control on this host blocks `_mupdf.pyd` at runtime.)

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
