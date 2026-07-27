# Claude Instructions

## Project Context

Autocert is a certificate automation module built as a plug-in service for a parent dashboard. The current repository state is a scaffold only: documentation, container setup, and workspace rules. Implementation should follow the architecture plan in `docs/architecture-prd.md`.

## Operating Rules

- Prefer Docker and Docker Compose for running, testing, and validating this project.
- Do not assume native npm or Python execution in this workspace unless the user explicitly asks for it.
- If a task requires running containers and Docker is unavailable, first verify whether Docker Desktop or the Docker daemon is running. If it is not running, tell the user to start Docker Desktop before retrying.
- Keep code loosely coupled, modular, and aligned with SOLID and DRY principles.
- Favor ports and adapters, explicit interfaces, and small focused modules.
- Avoid hardcoding environment-specific behavior in application logic when it belongs in configuration or container setup.
- Preserve the dashboard integration contract; do not introduce assumptions that require the parent dashboard to be modified.

## Architecture Guardrails

- Keep the FastAPI backend and React frontend separated by a clear API boundary.
- Avoid tightly coupled implementations between generation, storage, delivery, and approval flows.
- Keep batch, participant, certificate, and delivery responsibilities distinct.
- Respect the version-pinned template model and immutable import snapshot model described in the PRD.
- Use containerized commands for future development tasks unless the user says otherwise.

## Workflow Preference

- When asked to run or test code, use Docker Compose first.
- When a container is needed for validation, prefer `docker compose` over native tooling.
- If Docker is not running, surface that immediately instead of attempting native fallbacks.