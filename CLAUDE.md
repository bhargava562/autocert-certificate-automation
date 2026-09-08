# Claude Instructions — Autocert Certificate Automation

## Current Project Memory Checkpoint

Autocert is a plug-in certificate automation module built for an external parent dashboard. The current state is fully native (zero Docker), backed by Python 3.12+ and Supabase.

### 1. Current State of Repository
- **Database Architecture (9 Core Tables)**: Codified in `backend/supabase/migrations/`:
  - `data_sources`, `batches`, `batch_progress`, `participants`, `generation_tasks`, `certificates`, `delivery_tasks`, `deliveries`, `previews`.
- **Supabase Storage**: Active buckets `certificates` (10MB) and `templates` (25MB) provisioned and verified via `init_storage.py`.
- **Dynamic Dimension & Resolution-Independent Engine**:
  - **Zero Fixed Dimensions**: Certificates are never bound to static pixel dimensions or aspect ratios. The module dynamically adapts to any resolution (720p, 1080p, 2000x1414, 4K, 300+ DPI print) and aspect ratio (Landscape, Portrait, Square).
  - **Proportional Coordinates & Scaling**: All positions (`x_pct`, `y_pct`), widths (`max_w_pct`), target font sizes (`font_size_pct`), and dynamic downscaling limits (`min_font_size_pct`) are proportional relative metrics (0.0 to 1.0).
  - **Adaptive Step Sizing**: `TextFittingService.fit_text_to_width` scales dynamically with canvas height and uses an adaptive step size (`max(1, int(target_size * 0.025))`) to avoid performance bottlenecks on massive ultra-HD canvases.
  - **Defensive Area Clearing**: Manifest-configured `clear_area` and `clear_bg_color` wipe placeholder slots dynamically to guarantee zero text ghosting across any background.
- **Master PNG Asset Pipeline (Zero Static PDF Dependency)**:
  - Master template is the cleaned, high-resolution PNG asset (`Black Gold Formal Appreciation Certificate.png`) with sample text permanently wiped. Static PDF templates without editable fields/placeholders are strictly discontinued.
- **Decoupled Output Generation (Mutually Exclusive)**:
  - Formats are generated strictly separately per run (`--format png` generates all PNG images; `--format pdf` compiles directly into printable PDFs from the master image). Output folders are automatically cleaned before batch generation to eliminate mixed artifacts.
- **Execution Modes**:
  - **Local Mode**: Reads from `backend/sample_templates/` and outputs directly to `backend/sample_templates/output/`.
  - **Cloud Mode**: Reads from Supabase `templates` bucket and uploads to `certificates` bucket with signed URLs.
- **Mock Dataset**: 5 diverse participants in `backend/sample_data/mock_participants.json`.
- **Dependencies & Environments**: Pinned exact versions in `backend/requirements.txt`, verified inside `.venv`.
- **Protected Main Branch**: GitHub branch protection active on `main`; all updates are merged via pull requests.

---

## Domain Architecture Flow

```text
Data Source ➔ Batch ➔ Participant Snapshot ➔ Generation Task ➔ Certificate ➔ Delivery Task ➔ Delivery
                     ├── Batch Progress (Decoupled Atomic Counters)
                     └── Preview (Human Approval Gate Evidence: First 5, Random 5, Failure Report)
```

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

---

## Technical Guardrails

- **Zero Docker**: Run natively on host Windows environment.
- **SOLID Design**: All certificate generators implement `CertificateEngine` protocol; orchestrator depends on abstractions, not concrete engines.
- **Dynamic Mapping**: Never use random/arbitrary coordinates. Use normalized percentages, dynamic font downscaling, and text bounding box calculations.