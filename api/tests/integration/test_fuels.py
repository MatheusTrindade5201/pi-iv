import pytest
from fastapi.testclient import TestClient

from app.models import ETHANOL_ID, FLEX_ID, GASOLINE_ID

pytestmark = pytest.mark.integration


def test_list_fuels(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/fuels", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == [
        {"id": str(GASOLINE_ID), "name": "Gasolina"},
        {"id": str(ETHANOL_ID), "name": "Etanol"},
        {"id": str(FLEX_ID), "name": "Flex"},
    ]


def test_list_fuels_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/fuels").status_code == 401
