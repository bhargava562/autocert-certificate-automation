# AGENTS.md

## Repository Rules For Agents

This repository contains the backend and database architecture for the Autocert Certificate Automation Module. Treat `docs/architecture-prd.md` as the source of truth for architecture and delivery phases.

### Mandatory Coding Principles

- Keep implementations loosely coupled.
- Follow SOLID and DRY principles.
- Prefer small composable services over monolithic modules.
- Use explicit interfaces and dependency injection where it improves testability and clarity.
- Do not make the frontend and backend depend on each other's internal structure.

### Native-First Workflow (Zero Docker)

- All development, testing, and runtime checks must run **natively** on the host environment.
- Do **not** use or introduce Docker, Docker Compose, or container wrappers.
- Use native Python (3.12+) with virtual environments (`.venv`) for the FastAPI backend.
- Use native Node (v20+/v24+) and npm for tooling and future frontend tasks.
- Database and file storage run directly against **Supabase** (PostgreSQL & Supabase Storage).

### Environment & Security Rules

- `backend/.env` contains sensitive live Supabase credentials. It **must never be modified or deleted**.
- Always maintain `backend/.env.example` when introducing new configuration keys (e.g. CORS, ports, external service keys).

### Mandatory Execution & Git Workflow Rules

1. **Initialize Python Virtual Environment First**:
   - Always initialize and verify the Python virtual environment (`.venv` in `backend/`) before executing scripts, installing dependencies, or running backend commands.
   - Activate `.venv` explicitly prior to running any backend process.
2. **Install Modules Only Inside Activated Venv**:
   - Never install packages into the global Python environment.
   - Always install modules after activating `.venv` (e.g. `.venv\Scripts\pip install ...`), and document dependencies in `backend/requirements.txt`.
3. **Compile & Validate Properly**:
   - Before completing tasks, always compile and validate code properly (e.g. `python -m py_compile`, test execution, or linter validation).
   - Ensure all SQL files are syntactically valid PostgreSQL statements.
4. **Commit and Push Whenever Required**:
   - Create atomic, descriptive git commits whenever a milestone, feature, or requested change is completed.
   - Push commits to the remote repository (`origin/main`) to keep progress synchronized and safe.

### Project Architecture Notes

- FastAPI backend lives in `backend/`.
- Supabase SQL migrations, storage setup, seed files, and migration runners live in `backend/supabase/`.
- React frontend placeholder lives in `frontend/`.
- The architecture plan and phase breakdown live in `docs/architecture-prd.md`.
- Keep documentation, scaffolding, and runtime concerns separated.