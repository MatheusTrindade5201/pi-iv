import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core.config import Settings
from app.main import create_app

pytestmark = pytest.mark.unit


class UnavailableDatabaseSession:
    def __enter__(self) -> "UnavailableDatabaseSession":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def execute(self, *args: object, **kwargs: object) -> None:
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))


def test_health_returns_503_when_database_is_unavailable(settings: Settings) -> None:
    app = create_app(settings)
    app.state.session_factory = UnavailableDatabaseSession

    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "unavailable"}
