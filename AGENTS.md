# AGENTS.md

## Repository Rules For Agents — Autocert Certificate Automation

This repository contains the backend and database architecture for the Autocert Certificate Automation Module. Treat `docs/architecture-prd.md` and `docs/certificate-engine-architecture.md` as the source of truth for architecture, delivery phases, and modular engine design.

---

## Current Project Memory Checkpoint (State of Repository)

### 1. What Has Been Completed & Verified
- **Native-First Architecture (Zero Docker)**: All container files removed; 100% native execution on Python 3.12+ (`.venv`) and Node.
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
- **Supabase Storage**: Active buckets `certificates` (10MB) and `templates` (25MB) provisioned and verified via `backend/supabase/init_storage.py`.
- **Dynamic Dimension & Resolution-Independent Engine**:
  - **Zero Fixed Dimensions**: Certificates are never bound to static sizes or fixed pixel coordinates. The module dynamically adapts to any resolution (720p, 1080p, 2000x1414, 4K, 300+ DPI print) and aspect ratio (Landscape, Portrait, Square).
  - **Proportional Coordinates & Scaling**: All positions (`x_pct`, `y_pct`), widths (`max_w_pct`), target font sizes (`font_size_pct`), and dynamic downscaling limits (`min_font_size_pct`) are proportional relative metrics (0.0 to 1.0).
  - **Adaptive Step Sizing**: `TextFittingService.fit_text_to_width` scales dynamically with canvas height and uses an adaptive step size (`max(1, int(target_size * 0.025))`) to avoid performance bottlenecks on massive ultra-HD canvases.
  - **Defensive Area Clearing**: Manifest-configured `clear_area` and `clear_bg_color` wipe placeholder slots dynamically to guarantee zero text ghosting across any background.
- **Master PNG Asset Pipeline (Zero Static PDF Dependency)**:
  - Master template is the cleaned, high-resolution PNG asset (`Black Gold Formal Appreciation Certificate.png`) with sample text permanently wiped. Static PDF templates without editable fields/placeholders are strictly discontinued.
- **Decoupled Output Generation (Mutually Exclusive)**:
  - Formats are generated strictly separately per run (`--format png` generates all PNG images; `--format pdf` compiles directly into printable PDFs from the master image). Output folders are automatically cleaned before batch generation to eliminate mixed artifacts.
- **Dependencies & Environments**: Pinned exact versions in `backend/requirements.txt`, installed and validated inside `.venv`.
- **Protected Main Branch**: GitHub branch protection active on `main`; all updates are merged via pull requests.

### 2. Next Action on Standby
- Ready for batch generation, API service exposure, or database integration as instructed by user.

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