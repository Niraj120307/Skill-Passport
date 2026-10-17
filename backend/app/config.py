"""Application configuration, loaded from environment variables / backend/.env."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


class Settings:
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{(BACKEND_DIR / 'data' / 'skill_passport.db').as_posix()}")
    github_token: str | None = os.getenv("GITHUB_TOKEN") or None
    github_api_base: str = os.getenv("GITHUB_API_BASE", "https://api.github.com")
    github_timeout_seconds: int = _int("GITHUB_TIMEOUT_SECONDS", 25)
    # Repository download / scan limits
    max_repo_zip_mb: int = _int("MAX_REPO_ZIP_MB", 40)
    max_files_scanned: int = _int("MAX_FILES_SCANNED", 600)
    max_file_kb: int = _int("MAX_FILE_KB", 300)
    max_commits: int = _int("MAX_COMMITS", 100)
    max_file_history_lookups: int = _int("MAX_FILE_HISTORY_LOOKUPS", 5)
    # Resume limits
    max_resume_mb: int = _int("MAX_RESUME_MB", 5)
    # CORS + public link base
    cors_origins: list[str] = [
        o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()
    ]
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "http://localhost:5173")


settings = Settings()
