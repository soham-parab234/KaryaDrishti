"""Database session and connection management."""

from collections.abc import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from backend.app.core.config import settings
from backend.app.db.base import Base

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """Dependency that yields a database session and safely closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db(target_engine=None) -> None:
    """Initialize database tables for all declared models."""
    eng = target_engine or engine
    # Import all models before create_all to ensure they register on Base.metadata
    import backend.app.models.ingestion  # noqa: F401
    import backend.app.models.occupation  # noqa: F401
    import backend.app.models.analytics  # noqa: F401
    import backend.app.models.forecasting  # noqa: F401
    import backend.app.models.alerts  # noqa: F401
    import backend.app.models.recommendations  # noqa: F401
    import backend.app.models.audit  # noqa: F401
    Base.metadata.create_all(bind=eng)

    # Lightweight migration check for existing SQLite databases
    with eng.connect() as conn:
        try:
            # forecast_points data_status
            cols_fp = [row[1] for row in conn.execute(text("PRAGMA table_info(forecast_points)")).fetchall()]
            if cols_fp and "data_status" not in cols_fp:
                conn.execute(text("ALTER TABLE forecast_points ADD COLUMN data_status VARCHAR(50) DEFAULT 'SYNTHETIC_DEMO' NOT NULL"))

            # forecast_runs data_status
            cols_fr = [row[1] for row in conn.execute(text("PRAGMA table_info(forecast_runs)")).fetchall()]
            if cols_fr and "data_status" not in cols_fr:
                conn.execute(text("ALTER TABLE forecast_runs ADD COLUMN data_status VARCHAR(50) DEFAULT 'SYNTHETIC_DEMO' NOT NULL"))

            # early_warning_alerts triage columns
            cols_al = [row[1] for row in conn.execute(text("PRAGMA table_info(early_warning_alerts)")).fetchall()]
            if cols_al:
                if "triage_status" not in cols_al:
                    conn.execute(text("ALTER TABLE early_warning_alerts ADD COLUMN triage_status VARCHAR(50) DEFAULT 'NEW' NOT NULL"))
                if "triage_note" not in cols_al:
                    conn.execute(text("ALTER TABLE early_warning_alerts ADD COLUMN triage_note VARCHAR(255)"))

            # audit_events cryptographic hash chaining columns
            cols_ae = [row[1] for row in conn.execute(text("PRAGMA table_info(audit_events)")).fetchall()]
            if cols_ae:
                if "prev_hash" not in cols_ae:
                    conn.execute(text("ALTER TABLE audit_events ADD COLUMN prev_hash VARCHAR(64)"))
                if "record_hash" not in cols_ae:
                    conn.execute(text("ALTER TABLE audit_events ADD COLUMN record_hash VARCHAR(64)"))

            conn.commit()
        except Exception:
            pass

def check_db_connection(target_engine=None) -> bool:
    """Check whether the database is accessible by running a lightweight query."""
    eng = target_engine or engine
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
