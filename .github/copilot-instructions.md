# GitHub Copilot Instructions — Autocert Certificate Automation

## Project Memory & Context

Autocert is a plug-in certificate automation module for an external dashboard, built with:
- **Backend:** Python (3.12+) with FastAPI and Uvicorn.
- **Database:** Supabase PostgreSQL (managed via SQL migrations in `backend/supabase/migrations/`).
- **Storage:** Supabase Storage (`certificates` and `templates` buckets, accessed via signed URLs).
- **Architecture Source of Truth:** `docs/architecture-prd.md`.
- **Core Domain Flow:** `Data Source` ➔ `Batch` ➔ `Participant Snapshot` ➔ `Generation Task` ➔ `Certificate` ➔ `Delivery Task` ➔ `Delivery` (with `Batch Progress` atomic counters and `Preview` approval gate).

### Confirmed 9 Core Database Tables
1. `data_sources` — Records origin (CSV, Google Sheets, Google Forms, Manual).
2. `batches` — Tracks FSM state (`CREATED` to `COMPLETED` / `PARTIAL_SUCCESS`), template pinning (`template_id`, `template_version`).
3. `batch_progress` — Decoupled atomic counters (`total_count`, `generated_count`, `sent_count`, `failed_count`) to avoid row locks.
4. `participants` — Immutable snapshot frozen at import time with dynamic `participant_data JSONB` and validation status.
5. `generation_tasks` — Task-level granularity for per-row retries at scale (up to 50k rows).
6. `certificates` — Generated metadata, version pinning, file hashes, and storage paths.
7. `delivery_tasks` — Individual delivery jobs with unique `idempotency_key = sha256(certificate_id)` for crash safety.
8. `deliveries` — Provider dispatch records storing message IDs and errors for zero-log troubleshooting.
9. `previews` — Preview certificate references (first 5, random 5, failure reports) for the human approval gate.

---

## Operating & Workflow Rules

### 1. Python Virtual Environment First (Mandatory)
- **Always initialize/verify Python virtual environment (`.venv`) before doing anything in the backend:**
  ```powershell
  # Windows
  cd backend
  if (!(Test-Path .venv)) { python -m venv .venv }
  .venv\Scripts\Activate.ps1
  ```
- **Never install Python packages globally.** Always ensure `.venv` is activated before running `pip install`.
- Always track newly introduced backend packages in `backend/requirements.txt` or `pyproject.toml`.

### 2. Native-First Workflow (Strictly Zero Docker)
- All development, testing, and runtime checks must run **natively** on the host environment (Windows / PowerShell).
- Do **not** create, suggest, or introduce Dockerfiles, docker-compose files, or container wrappers.

### 3. Environment & Credentials Security
- `backend/.env` contains live, sensitive Supabase credentials. **It must NEVER be modified or deleted.**
- When introducing new environment variables (such as `CORS_ORIGINS`, `PORT`, service keys), document them in `backend/.env.example`.

### 4. Compilation, Quality & Validation
- Always validate code before committing:
  - Check Python syntax and types: `python -m py_compile <files>` or run test suites.
  - Verify SQL migration syntax against PostgreSQL 15+ standards.
  - Ensure zero unresolved linting/type errors.

### 5. Git Commit and Push Discipline
- Commit and push changes whenever a meaningful milestone or task is completed.
- Write clear, concise, and structured commit messages (e.g. `feat(supabase): ...`, `fix(backend): ...`, `docs: ...`).
- Verify `git status` before committing to avoid staging unintended or untracked sensitive files (`.env` must remain ignored).
- Push cleanly to the active branch (`origin/main`).
