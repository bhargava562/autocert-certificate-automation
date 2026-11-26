"""
Application Configuration
Loads settings safely from backend/.env without ever modifying or deleting it.
"""

import os
from dataclasses import dataclass
from typing import Optional, Tuple

DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
)


def _parse_cors_origins(raw: Optional[str]) -> Tuple[str, ...]:
    if not raw:
        return DEFAULT_CORS_ORIGINS
    origins = tuple(o.strip() for o in raw.split(",") if o.strip())
    return origins or DEFAULT_CORS_ORIGINS


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
    cors_origins: Tuple[str, ...] = DEFAULT_CORS_ORIGINS
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_name: str = "Autocert Certificates"
    smtp_from_email: Optional[str] = None
    smtp_timeout_seconds: int = 30
    default_min_font_size_pct: float = 0.015
    default_max_lines: int = 3

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

    smtp_user = env.get("SMTP_USER") or os.getenv("SMTP_USER")
    return Settings(
        supabase_url=env.get("SUPABASE_URL") or os.getenv("SUPABASE_URL"),
        supabase_publishable_key=env.get("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_PUBLISHABLE_KEY"),
        supabase_anon_key=env.get("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_ANON_KEY"),
        supabase_service_key=env.get("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_KEY"),
        database_url=env.get("DATABASE_URL") or os.getenv("DATABASE_URL"),
        environment=env.get("ENVIRONMENT", "development"),
        port=int(env.get("PORT", 8000)),
        host=env.get("HOST", "0.0.0.0"),
        cors_origins=_parse_cors_origins(env.get("CORS_ORIGINS") or os.getenv("CORS_ORIGINS")),
        smtp_host=env.get("SMTP_HOST") or os.getenv("SMTP_HOST", "smtp.gmail.com"),
        smtp_port=int(env.get("SMTP_PORT") or os.getenv("SMTP_PORT", 587)),
        smtp_user=smtp_user,
        smtp_password=env.get("SMTP_PASSWORD") or os.getenv("SMTP_PASSWORD"),
        smtp_from_name=env.get("SMTP_FROM_NAME") or os.getenv("SMTP_FROM_NAME", "Autocert Certificates"),
        smtp_from_email=env.get("SMTP_FROM_EMAIL") or os.getenv("SMTP_FROM_EMAIL") or smtp_user,
        smtp_timeout_seconds=int(env.get("SMTP_TIMEOUT_SECONDS") or os.getenv("SMTP_TIMEOUT_SECONDS") or 30),
        default_min_font_size_pct=float(
            env.get("DEFAULT_MIN_FONT_SIZE_PCT") or os.getenv("DEFAULT_MIN_FONT_SIZE_PCT") or 0.015
        ),
        default_max_lines=int(env.get("DEFAULT_MAX_LINES") or os.getenv("DEFAULT_MAX_LINES") or 3),
    )
