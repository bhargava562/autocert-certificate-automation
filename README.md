# Autocert Certificate Automation

Certificate Automation Module for a React dashboard frontend and FastAPI backend.

This repository is scaffolded as a self-contained module that the parent dashboard can integrate through a small contract surface. The implementation is intentionally not started yet; the current focus is repository structure and documentation.

Development and validation should run through Docker and Docker Compose. On this workspace, avoid native npm or Python execution unless explicitly requested.

## Table of Contents

- [Docker workflow](#docker-workflow)
- [Docs index](docs/README.md)
- [Architecture PRD](docs/architecture-prd.md)
- [Frontend scaffold](frontend/README.md)
- [Backend scaffold](backend/README.md)

## Docker Workflow

Use `docker compose` for local development, runtime checks, and test execution.

If Docker is not available, the first check is whether Docker Desktop is running in the host environment. If the daemon is unavailable, tell the user to start Docker Desktop before retrying container commands.

## Summary

The module is designed to accept participant data from multiple sources, generate certificates from a version-pinned dashboard-owned template, support approval before any delivery, and scale safely through task-level retry and progress tracking.

The full product and architecture plan is documented under `docs/`.
