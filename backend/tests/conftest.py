import os

# Must be set BEFORE importing app.main / app.config so pydantic-settings can
# construct Settings() without erroring on missing required fields. There is
# no live Postgres in this environment, so DATABASE_URL points at a local
# SQLite file instead — see the note below on why it stays a real file
# rather than `sqlite:///:memory:`.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("OPENAI_API_KEY", "test-key")

import pytest
from fastapi.testclient import TestClient

from app.auth.jwt import create_access_token, hash_password
from app.database import Base, SessionLocal, engine, get_db
from app.main import app
from app.models.user import User

# NOTE: We deliberately reuse `app.database.engine` / `app.database.SessionLocal`
# (bound to DATABASE_URL=sqlite:///./test.db, a real file, set above) rather than
# spinning up a separate test-only engine. `pipeline_service.run_pipeline` opens
# its own DB session via `from app.database import SessionLocal` (background
# tasks have no request-scoped session), so if tests used a *different* engine
# object, data committed via the test fixtures/TestClient would be invisible to
# code under test that goes through `app.database.SessionLocal` directly, and
# vice versa. A file-based SQLite URL (not `:memory:`) also means we don't need
# `StaticPool`/`check_same_thread=False` tricks: SQLAlchemy's pysqlite dialect
# already pools file-based connections safely across threads, which matters
# because FastAPI runs sync dependencies (like `get_db`) in a threadpool.


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_db_file():
    """Remove the sqlite test DB file once the whole test session finishes."""
    db_path = os.path.join(os.path.dirname(__file__), "..", "test.db")
    yield
    engine.dispose()  # release pooled connections so the file can be deleted on Windows
    if os.path.isfile(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db):
    user = User(
        email="test@example.com",
        hashed_password=hash_password("password123"),
        full_name="Test User",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def other_user(db):
    user = User(
        email="other@example.com",
        hashed_password=hash_password("password123"),
        full_name="Other User",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    token = create_access_token({"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_auth_headers(other_user):
    token = create_access_token({"sub": str(other_user.id)})
    return {"Authorization": f"Bearer {token}"}
