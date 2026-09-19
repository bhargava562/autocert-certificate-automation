# Supabase Database & Storage Setup

This directory contains the database schema migrations, storage bucket provisioning, seed data, and migration runner scripts for the **Autocert Certificate Automation Backend**.

---

## Mandatory Workflow Rules

- **Initialize Virtual Environment First**: Ensure `backend/.venv` is active before executing Python scripts: `.venv\Scripts\Activate.ps1`.
- **Install Modules Inside Venv**: Run package installations (e.g. `pip install psycopg[binary]`) only within the active `.venv`.
- **Compile & Validate**: Verify all Python scripts (`python -m py_compile supabase/*.py`) and SQL syntax before completing work.
- **Git Commit & Push**: Commit milestone progress and push to `origin/main`.
- **Protect Credentials**: Never modify or delete `backend/.env`. Maintain `backend/.env.example`.

---

## Architecture & Tables

The schema implements the 9 core ERD tables derived from [`docs/architecture-prd.md`](../../docs/architecture-prd.md):

| # | Table | Description |
|---|---|---|
| 1 | `data_sources` | Records original data origins (CSV, Google Sheet, Google Form, Manual Form). |
| 2 | `batches` | Core batch entity with FSM status transitions (`CREATED` through `COMPLETED` / `PARTIAL_SUCCESS`). |
| 3 | `batch_progress` | Atomic shared counters (`total_count`, `generated_count`, `sent_count`, `failed_count`) to avoid lock contention on batches. |
| 4 | `participants` | Immutable snapshot of participant data frozen at import time with custom JSONB data and validation fields. |
| 5 | `generation_tasks` | Granular certificate generation units supporting individual row retry at scale. |
| 6 | `certificates` | Generated certificate metadata and storage paths. |
| 7 | `delivery_tasks` | Delivery jobs with `sha256(certificate_id)` unique idempotency key. |
| 8 | `deliveries` | Provider dispatch logs enabling zero-log troubleshooting. |
| 9 | `previews` | Sample certificates (first 5, random 5) and validation failure reports for human approval. |

---

## Directory Structure

```text
backend/supabase/
├── migrations/
│   ├── 20260907000001_initial_erd_schema.sql  # 9 tables, ENUMs, triggers, indexes, RLS
│   └── 20260907000002_storage_setup.sql       # Storage buckets and security policies
├── init_storage.py                            # Automatic storage bucket provisioner via REST
├── migrate.py                                 # Python migration runner with version tracking
├── migrate.js                                 # Node.js migration runner alternative
├── seed.sql                                   # End-to-end sample data
└── README.md                                  # This guide
```

---

## How to Apply Migrations

### Method 1: Automatic via Python Script
1. Ensure your PostgreSQL connection string (`DATABASE_URL`) is added to `backend/.env`:
   ```bash
   DATABASE_URL=postgresql://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
   ```
2. Run the migration script:
   ```bash
   python supabase/migrate.py
   ```
   To include sample seed data:
   ```bash
   python supabase/migrate.py --seed
   ```

### Method 2: Automatic via Node.js Script
1. Install `pg`:
   ```bash
   npm install pg
   ```
2. Run the script:
   ```bash
   node supabase/migrate.js
   # or with seed
   node supabase/migrate.js --seed
   ```

### Method 3: Supabase Web Dashboard (1-Click)
1. Open your [Supabase Project Dashboard](https://supabase.com/dashboard).
2. Go to the **SQL Editor** tab.
3. Paste the contents of `migrations/20260907000001_initial_erd_schema.sql` and click **Run**.
4. Paste the contents of `migrations/20260907000002_storage_setup.sql` and click **Run**.
5. (Optional) Paste `seed.sql` and click **Run** to load test data.

---

## Storage Buckets Provisioning

Storage buckets (`certificates` and `templates`) can be provisioned immediately using the `SUPABASE_SERVICE_KEY` in `backend/.env`:

```bash
python supabase/init_storage.py
```

This communicates with the Supabase Storage REST API directly and creates private buckets with file size limits:
- `certificates`: 10MB limit (PDF, PNG, JPEG, WebP)
- `templates`: 25MB limit (PDF, PNG, SVG, JSON)
