import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from unittest.mock import patch
import fakeredis
from rq import Queue
from alembic.config import Config
from alembic import command

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app


@pytest.fixture(scope="session")
def test_engine():
    test_database_url = os.getenv("TEST_DATABASE_URL")
    if not test_database_url:
        pytest.fail("TEST_DATABASE_URL must be set; refusing to use the development database")
    if test_database_url == settings.DATABASE_URL:
        pytest.fail("TEST_DATABASE_URL must point to a database separate from DATABASE_URL")

    engine = create_engine(test_database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def alembic_config(test_engine):
    """Create an Alembic config for the test database."""
    config = Config("alembic.ini")
    config.set_main_option(
        "sqlalchemy.url",
        test_engine.url.render_as_string(hide_password=False),
    )
    return config


@pytest.fixture(scope="session", autouse=True)
def run_migrations(alembic_config):
    """Run Alembic migrations on the test database once per session."""
    command.upgrade(alembic_config, "head")
    yield
    command.downgrade(alembic_config, "base")


@pytest.fixture
def db_session(test_engine, run_migrations):
    """Provide a transactional session for each test."""
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = testing_session()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def client(db_session: Session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def fake_redis():
    """Provide a fake Redis instance for testing."""
    return fakeredis.FakeRedis()


@pytest.fixture
def test_queue(fake_redis):
    """Provide a test RQ queue using fake Redis."""
    return Queue(connection=fake_redis)


@pytest.fixture(autouse=True)
def patch_queue(test_queue):
    """Patch the global RQ queue in app.core.queue and app.services.bookmark_service with the test queue."""
    with patch("app.core.queue.queue", test_queue), \
         patch("app.core.queue.redis_conn", test_queue.connection), \
         patch("app.services.bookmark_service.queue", test_queue):
        yield
