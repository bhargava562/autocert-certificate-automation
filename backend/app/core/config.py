"""
Application Configuration
Loads settings safely from backend/.env without ever modifying or deleting it.
"""

import os
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Settings:
    supabase_url: Optional[str]
    supabase_publishable_key: Optional[str]
    supabase_anon_key: Optional[str]
    supabase_service_key: Optional[str]
    database_url: Optional[str]
    environment: str = "development"
    port: int = 8000
    host: str = "0.0.0.0"

def load_settings(env_path: Optional[str] = None) -> Settings:
    if env_path is None:
        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        env_path = os.path.join(backend_dir, ".env")

    env = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()

    return Settings(
        supabase_url=env.get("SUPABASE_URL") or os.getenv("SUPABASE_URL"),
        supabase_publishable_key=env.get("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_PUBLISHABLE_KEY"),
        supabase_anon_key=env.get("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_ANON_KEY"),
        supabase_service_key=env.get("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_KEY"),
        database_url=env.get("DATABASE_URL") or os.getenv("DATABASE_URL"),
        environment=env.get("ENVIRONMENT", "development"),
        port=int(env.get("PORT", 8000)),
        host=env.get("HOST", "0.0.0.0"),
    )
