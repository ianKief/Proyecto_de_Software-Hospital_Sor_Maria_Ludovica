
import pytest

from src.core.db import db
from src.web import create_app


@pytest.fixture
def app(monkeypatch):
    """Aplicación con una base SQLite aislada para cada test."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    app = create_app(env="testing")
    app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret",
    )

    with app.app_context():
        db.create_all()

        try:
            yield app
        finally:
            db.session.remove()
            db.drop_all()
