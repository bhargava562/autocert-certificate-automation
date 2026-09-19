# Autocert Certificate Automation

Certificate Automation Module designed for a FastAPI backend and Supabase infrastructure (PostgreSQL database & Supabase Storage).

This repository is built as a self-contained module that an external dashboard can integrate through a well-defined contract surface.

## Table of Contents

- [Native Workflow](#native-workflow)
- [Mandatory Workflow Rules](#mandatory-workflow-rules)
- [Supabase Migrations & Storage](#supabase-migrations--storage)
- [Docs Index](docs/README.md)
- [Architecture PRD](docs/architecture-prd.md)
- [Backend Scaffold](backend/README.md)
- [Frontend Scaffold](frontend/README.md)

## Native Workflow

All local development and execution runs natively without Docker:

- **Backend:** Python 3.12+ with virtual environment (`.venv`), FastAPI, Uvicorn.
- **Database & Storage:** Supabase PostgreSQL and Supabase Storage.
- **Frontend:** Node v20+/v24+ and npm (for future frontend integration).

## Mandatory Workflow Rules

All developers and agents working in this repository must follow these rules:
1. **Initialize Virtual Environment First**: Always create and activate `backend/.venv` prior to running scripts or commands.
2. **Install Modules Inside Active Venv**: Never install Python modules globally; only run `pip install` when `.venv` is activated.
3. **Compile & Validate Properly**: Run code validation (e.g. `python -m compileall .` or tests) before finishing work to guarantee zero compile/syntax errors.
4. **Commit and Push Whenever Required**: Maintain an atomic, clean Git history and push commits to `origin/main` as milestones and tasks are completed.
5. **Protect Environment Secrets**: `backend/.env` contains live credentials and must never be modified or deleted. Always document new keys in `backend/.env.example`.

## Supabase Migrations & Storage

The database architecture implements 9 core tables matching the PRD:
1. `data_sources`
2. `batches`
3. `batch_progress`
4. `participants` (immutable snapshot)
5. `generation_tasks`
6. `certificates`
7. `delivery_tasks` (idempotency key via `sha256(certificate_id)`)
8. `deliveries` (zero-log troubleshooting)
9. `previews` (human approval gate)

SQL migrations and migration runners live in `backend/supabase/`. See [backend/supabase/README.md](backend/supabase/README.md) for full instructions.

### Quick Start:
```bash
# Provision storage buckets
python backend/supabase/init_storage.py

# Run SQL migrations (with DATABASE_URL configured in backend/.env)
python backend/supabase/migrate.py
```

## Summary

The module accepts participant data from multiple sources (CSV, Google Sheets, Google Forms, manual entry), normalizes it into an immutable snapshot, generates certificates against a version-pinned template, enforces a human approval gate with preview evidence, and scales safely with task-level retry and atomic progress counters.
