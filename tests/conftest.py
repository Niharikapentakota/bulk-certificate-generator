import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db

@pytest.fixture
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Make background generation use the test database by patching the module globals.
    import app.services.generator as generator
    monkeypatch.setattr(generator, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(generator, "OUTPUT_DIR", tmp_path / "generated")
    (tmp_path / "generated").mkdir()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
