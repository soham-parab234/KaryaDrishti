"""Pytest configuration and fixtures with isolated temporary SQLite database."""

from collections.abc import Generator
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.main import app

# Create in-memory SQLite database with StaticPool for test isolation
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create all schema tables in test engine once per test session."""
    import backend.app.models.ingestion  # noqa: F401
    import backend.app.models.occupation  # noqa: F401
    import backend.app.models.analytics  # noqa: F401
    import backend.app.models.forecasting  # noqa: F401
    import backend.app.models.alerts  # noqa: F401
    import backend.app.models.recommendations  # noqa: F401
    import backend.app.models.audit  # noqa: F401
    Base.metadata.create_all(bind=test_engine)

    from backend.app.services.nco_reference import seed_pilot_baseline_nco
    from backend.app.services.analytics_service import seed_pilot_baseline_analytics
    with TestingSessionLocal() as session:
        seed_pilot_baseline_nco(session)
        seed_pilot_baseline_analytics(session)

    yield
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide a transactional database session for an individual test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Provide a FastAPI TestClient with the database dependency overridden."""
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
