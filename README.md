# Autocert Certificate Automation

Certificate Automation Module for a React dashboard frontend and FastAPI backend.

This repository is scaffolded as a self-contained module that the parent dashboard can integrate through a small contract surface. The implementation is intentionally not started yet; the current focus is repository structure and documentation.

## Table of Contents

- [Docs index](docs/README.md)
- [Architecture PRD](docs/architecture-prd.md)
- [Frontend scaffold](frontend/README.md)
- [Backend scaffold](backend/README.md)

## Summary

The module is designed to accept participant data from multiple sources, generate certificates from a version-pinned dashboard-owned template, support approval before any delivery, and scale safely through task-level retry and progress tracking.

The full product and architecture plan is documented under `docs/`.
