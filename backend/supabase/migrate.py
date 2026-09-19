#!/usr/bin/env python3
"""
Supabase Migration Runner (Python)
Applies SQL migration files in numerical order from backend/supabase/migrations/
and tracks applied versions in the `_schema_migrations` table.
"""

import os
import sys
import glob

def load_env(env_path: str) -> dict:
    env = {}
    if not os.path.exists(env_path):
        return env
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

def get_db_connection(db_url: str):
    try:
        import psycopg
        return psycopg.connect(db_url, autocommit=False)
    except ImportError:
        pass

    try:
        import psycopg2
        return psycopg2.connect(db_url)
    except ImportError:
        pass

    return None

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.abspath(os.path.join(script_dir, ".."))
    env_path = os.path.join(backend_dir, ".env")
    env = load_env(env_path)

    db_url = env.get("DATABASE_URL") or os.environ.get("DATABASE_URL")

    print("=" * 60)
    print("Autocert Supabase Migration Runner")
    print("=" * 60)

    migrations_dir = os.path.join(script_dir, "migrations")
    sql_files = sorted(glob.glob(os.path.join(migrations_dir, "*.sql")))

    if not sql_files:
        print(f"No SQL migration files found in {migrations_dir}")
        return

    print(f"Found {len(sql_files)} migration files:")
    for f in sql_files:
        print(f"  - {os.path.basename(f)}")
    print()

    if not db_url or "your-project-ref" in db_url:
        print("[NOTICE] Direct DATABASE_URL is not configured in backend/.env.")
        print("To apply migrations automatically via Python, append your PostgreSQL connection string:")
        print("  DATABASE_URL=postgresql://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres")
        print()
        print("Alternatively, you can copy-paste the SQL files directly into the Supabase SQL Editor:")
        for f in sql_files:
            print(f"  -> {f}")
        return

    conn = get_db_connection(db_url)
    if conn is None:
        print("[ERROR] Neither 'psycopg' nor 'psycopg2' is installed in the current Python environment.")
        print("Install psycopg via: pip install psycopg[binary]")
        return

    try:
        with conn.cursor() as cur:
            # 1. Create migration tracking table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS _schema_migrations (
                    version VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
            """)
            conn.commit()

            # 2. Get already applied migrations
            cur.execute("SELECT version FROM _schema_migrations;")
            applied = set(row[0] for row in cur.fetchall())

            # 3. Apply pending migrations
            for f in sql_files:
                filename = os.path.basename(f)
                if filename in applied:
                    print(f"  [SKIP] {filename} (already applied)")
                    continue

                print(f"  [APPLYING] {filename}...")
                with open(f, "r", encoding="utf-8") as sql_file:
                    sql_content = sql_file.read()

                cur.execute(sql_content)
                cur.execute(
                    "INSERT INTO _schema_migrations (version) VALUES (%s);",
                    (filename,)
                )
                conn.commit()
                print(f"  [SUCCESS] {filename} applied successfully.")

            # Check for --seed argument
            if "--seed" in sys.argv:
                seed_file = os.path.join(script_dir, "seed.sql")
                if os.path.exists(seed_file):
                    print(f"\n  [APPLYING SEED] {os.path.basename(seed_file)}...")
                    with open(seed_file, "r", encoding="utf-8") as sf:
                        cur.execute(sf.read())
                    conn.commit()
                    print("  [SUCCESS] Seed data loaded successfully.")

        print("\nAll database migrations are up to date.")
    except Exception as e:
        conn.rollback()
        print(f"\n[FAILED] Error applying migrations: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
