# Backend

FastAPI backend service for the Autocert certificate automation module.

## Setup & Native Workflow

This backend runs natively with Python 3.12+.

### 1. Mandatory Virtual Environment Rules
Always initialize and activate `.venv` before starting anything or installing packages:
```powershell
# Navigate to backend directory
cd backend

# Create virtual environment if it does not exist
python -m venv .venv

# Activate on Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Activate on Unix/macOS
source .venv/bin/activate
```

**Rule:** Always install dependencies **after** activating `.venv`:
```powershell
pip install -r requirements.txt
```

### 2. Environment Configuration
Credentials and settings are managed in `.env` (see `.env.example` for variable documentation):
> [!CAUTION]
> `backend/.env` contains live credentials and **must never be modified or deleted**.

### 3. Compilation & Validation
Always compile and test code before finishing a task:
```powershell
# Syntax / compile check
python -m compileall .
```

### 4. Git Commit and Push
- Commit code changes cleanly and push to `origin/main` whenever a task or feature is completed.

### 5. Database & Storage Migrations
SQL migration files and runners live in `supabase/`:
- `supabase/migrations/`: PostgreSQL migration files (the 9 core ERD tables).
- `supabase/init_storage.py`: Provisions Supabase Storage buckets (`certificates`, `templates`).
- `supabase/migrate.py`: Python migration runner.
- `supabase/migrate.js`: Node.js migration runner alternative.
- `supabase/seed.sql`: Realistic seed data.

To provision storage buckets:
```powershell
python supabase/init_storage.py
```

To run migrations:
```powershell
python supabase/migrate.py
```

See [`supabase/README.md`](supabase/README.md) for full database documentation.
