"""Application settings and constants."""

from pathlib import Path
import os
import re

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SQLITE_PATH = DATA_DIR / "lmis.db"
DEFAULT_DB_URL = f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"

def _load_env_file_safely(paths: list[Path]) -> None:
    """Safely populate os.environ from local .env files if present without external dependencies."""
    for p in paths:
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
            except Exception:
                pass

_load_env_file_safely([BASE_DIR / ".env", BASE_DIR.parent / ".env"])

class Settings:
    PROJECT_NAME: str = "LMIS Forecasting Engine API"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = (
        "AI-Enabled Labour Market Intelligence & Skill Demand-Supply Forecasting Engine API. "
        "National Skill Demand-Supply Forecasting and Decision Support Platform."
    )
    API_PREFIX: str = "/api"

    DATABASE_URL: str = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

    # AI Assistant Configuration (Single Configurable Provider: Google Gemini)
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "gemini")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    GEMINI_TIMEOUT_SECONDS: float = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "25.0"))

    # Ingestion constraints
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB limit
    ALLOWED_SOURCE_SYSTEMS: tuple[str, ...] = (
        "NCS_FEED",
        "PORTAL_SCRAPE",
        "SCHEME_MIS",
        "ENTERPRISE_SURVEY",
    )

    # Valid census/standard district code regex (e.g. MH_PUN, MH_NSK, KA_BLR, DL_NEW)
    DISTRICT_CODE_PATTERN: re.Pattern = re.compile(r"^[A-Z]{2}_[A-Z0-9]{3,5}$")

    # Canonical required and optional CSV fields
    REQUIRED_CSV_COLUMNS: tuple[str, ...] = (
        "posting_id",
        "raw_title",
        "district_code",
        "observation_date",
        "source_system",
    )
    OPTIONAL_CSV_COLUMNS: tuple[str, ...] = (
        "vacancy_count",
    )

settings = Settings()
