# Claude Instructions

## Project Context

Autocert is a certificate automation module built as a plug-in service for a parent dashboard. Implementation follows the architecture plan in `docs/architecture-prd.md` and the 9-table ERD schema managed in `backend/supabase/`.

## Operating Rules

- Use native Python (3.12+) and native Node (20+/24+) execution for all tasks.
- Do not introduce Docker, Docker Compose, or container setups.
- Never modify or delete `backend/.env`. Maintain `backend/.env.example` when adding configuration options.
- Keep code loosely coupled, modular, and aligned with SOLID and DRY principles.
- Favor ports and adapters, explicit interfaces, and small focused modules.
- Preserve the dashboard integration contract; do not introduce assumptions that require the parent dashboard to be modified.

## Mandatory Execution & Git Workflow Rules

1. **Initialize Python Virtual Environment First**:
   - Always initialize the Python virtual environment (`.venv` in `backend/`) before executing scripts, running tests, or installing dependencies.
   - Always activate `.venv` explicitly before any command: `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (Unix).
2. **Install Modules Only Inside Activated Venv**:
   - Never install packages into the host's global environment.
   - Run `pip install` only after `.venv` is active, and update `backend/requirements.txt`.
3. **Compile & Validate Properly**:
   - Always validate Python code (`python -m py_compile ...` or pytest) and SQL syntax before declaring a task finished.
   - Maintain zero syntax or runtime import errors.
4. **Commit and Push Whenever Required**:
   - Stage and commit changes with clear, descriptive commit messages upon completing significant tasks or phases.
   - Push committed code to the active git branch (`git push origin main`) to keep work durable and synchronized.

## Architecture Guardrails

- Keep the FastAPI backend and React frontend separated by a clear API boundary.
- Avoid tightly coupled implementations between generation, storage, delivery, and approval flows.
- Keep batch, participant, certificate, and delivery responsibilities distinct.
- Respect the version-pinned template model and immutable import snapshot model described in the PRD.
- Follow the 9 core ERD tables: `data_sources`, `batches`, `batch_progress`, `participants`, `generation_tasks`, `certificates`, `delivery_tasks`, `deliveries`, `previews`.
- Storage is managed in Supabase Storage (`certificates` and `templates` buckets).

## Workflow Preference

- Run backend commands directly: `python -m venv .venv`, `pip install ...`, `uvicorn main:app --reload`.
- Run migrations via `python supabase/migrate.py` or `node supabase/migrate.js`.
- Provision storage buckets via `python supabase/init_storage.py`.