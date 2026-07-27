# AGENTS.md

## Repository Rules For Agents

This repository is scaffold-only. Treat `docs/architecture-prd.md` as the source of truth for architecture and delivery phases.

### Mandatory Coding Principles

- Keep implementations loosely coupled.
- Follow SOLID and DRY principles.
- Prefer small composable services over monolithic modules.
- Use explicit interfaces and dependency injection where it improves testability and clarity.
- Do not make the frontend and backend depend on each other's internal structure.

### Container-First Workflow

- Use Docker and Docker Compose for runtime checks, development runs, and validation.
- Do not rely on native npm or Python commands unless the user explicitly requests them.
- If a task depends on Docker and the daemon is not available, tell the user to start Docker Desktop before proceeding.

### Project Architecture Notes

- React frontend lives in `frontend/`.
- FastAPI backend lives in `backend/`.
- The architecture plan and phase breakdown live in `docs/architecture-prd.md`.
- Keep documentation, scaffolding, and runtime concerns separated.

### Memory And Context

- Remember the user's preference to run and test through Docker instead of native tools.
- Remember the Docker Desktop availability check: if Docker is unavailable, report that to the user and ask them to start Docker Desktop.
- Keep these preferences active unless the user explicitly overrides them.