import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Shift, ShiftStatus, User
from tests.factories import make_earning, make_shift, make_user, make_vehicle

pytestmark = pytest.mark.integration


@pytest.fixture
def shift(db_session: Session, user: User) -> Shift:
    return make_shift(
        db_session,
        user,
        make_vehicle(db_session, user),
        started_at=datetime.now(UTC) - timedelta(hours=2),
    )


def url(shift_id: uuid.UUID, earning_id: str | uuid.UUID | None = None) -> str:
    base = f"/api/v1/shifts/{shift_id}/earnings"
    return f"{base}/{earning_id}" if earning_id else base


def partial_earnings(client: TestClient, headers: dict[str, str]) -> str:
    return client.get("/api/v1/shifts/current", headers=headers).json()["summary"]["earnings_total"]


def test_add_earning(client: TestClient, auth_headers: dict[str, str], shift: Shift) -> None:
    response = client.post(
        url(shift.id), json={"amount": "20", "platform": "iFood"}, headers=auth_headers
    )

    assert response.status_code == 201
    body = response.json()
    assert body["shift_id"] == str(shift.id)
    assert body["amount"] == "20.00"
    assert body["platform"] == "iFood"
    assert body["earned_at"] is not None
    assert partial_earnings(client, auth_headers) == "20.00"


def test_list_earnings_in_chronological_order(
    client: TestClient, auth_headers: dict[str, str], shift: Shift
) -> None:
    later = (shift.started_at + timedelta(minutes=90)).isoformat()
    earlier = (shift.started_at + timedelta(minutes=30)).isoformat()
    client.post(url(shift.id), json={"amount": "8", "earned_at": later}, headers=auth_headers)
    client.post(url(shift.id), json={"amount": "5", "earned_at": earlier}, headers=auth_headers)

    response = client.get(url(shift.id), headers=auth_headers)

    assert response.status_code == 200
    assert [earning["amount"] for earning in response.json()] == ["5.00", "8.00"]


def test_overwrite_last_earning(
    client: TestClient, auth_headers: dict[str, str], shift: Shift
) -> None:
    client.post(url(shift.id), json={"amount": "5"}, headers=auth_headers)
    last = client.post(url(shift.id), json={"amount": "20"}, headers=auth_headers).json()

    response = client.patch(url(shift.id, last["id"]), json={"amount": "12"}, headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["amount"] == "12.00"
    assert response.json()["earned_at"] == last["earned_at"]
    assert partial_earnings(client, auth_headers) == "17.00"


def test_delete_earning(client: TestClient, auth_headers: dict[str, str], shift: Shift) -> None:
    earning = client.post(url(shift.id), json={"amount": "20"}, headers=auth_headers).json()

    response = client.delete(url(shift.id, earning["id"]), headers=auth_headers)

    assert response.status_code == 204
    assert client.get(url(shift.id), headers=auth_headers).json() == []
    assert partial_earnings(client, auth_headers) == "0.00"


def test_finished_shift_earnings_are_read_only(
    client: TestClient, auth_headers: dict[str, str], shift: Shift, db_session: Session
) -> None:
    earning = make_earning(db_session, shift, amount=Decimal("30.00"))
    client.post(f"/api/v1/shifts/{shift.id}/finish", headers=auth_headers)

    responses = [
        client.post(url(shift.id), json={"amount": "5"}, headers=auth_headers),
        client.patch(url(shift.id, earning.id), json={"amount": "1"}, headers=auth_headers),
        client.delete(url(shift.id, earning.id), headers=auth_headers),
    ]

    assert [r.status_code for r in responses] == [409, 409, 409]
    assert responses[0].json() == {"detail": "Expediente já encerrado"}
    assert [e["amount"] for e in client.get(url(shift.id), headers=auth_headers).json()] == [
        "30.00"
    ]
    detail = client.get(f"/api/v1/shifts/{shift.id}", headers=auth_headers).json()
    assert detail["status"] == ShiftStatus.FINISHED
    assert detail["summary"]["earnings_total"] == "30.00"


def test_earned_at_outside_shift_is_rejected(
    client: TestClient, auth_headers: dict[str, str], shift: Shift
) -> None:
    before_start = (shift.started_at - timedelta(minutes=1)).isoformat()

    response = client.post(
        url(shift.id), json={"amount": "5", "earned_at": before_start}, headers=auth_headers
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Horário do ganho fora do expediente"}


def test_shift_of_other_user_returns_404(
    client: TestClient, auth_headers: dict[str, str], db_session: Session
) -> None:
    other = make_user(db_session)
    other_shift = make_shift(db_session, other, make_vehicle(db_session, other))

    post = client.post(url(other_shift.id), json={"amount": "5"}, headers=auth_headers)
    get = client.get(url(other_shift.id), headers=auth_headers)

    assert (post.status_code, get.status_code) == (404, 404)
    assert post.json() == {"detail": "Expediente não encontrado"}


def test_earning_of_another_shift_of_same_user_returns_404(
    client: TestClient, auth_headers: dict[str, str], shift: Shift, db_session: Session, user: User
) -> None:
    finished = make_shift(
        db_session,
        user,
        make_vehicle(db_session, user),
        status=ShiftStatus.FINISHED,
        started_at=shift.started_at - timedelta(days=1),
    )
    foreign = make_earning(db_session, finished)

    response = client.patch(url(shift.id, foreign.id), json={"amount": "1"}, headers=auth_headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Ganho não encontrado"}


def test_earning_from_another_shift_cannot_be_edited(
    client: TestClient, auth_headers: dict[str, str], shift: Shift, db_session: Session
) -> None:
    other = make_user(db_session)
    foreign = make_earning(
        db_session, make_shift(db_session, other, make_vehicle(db_session, other))
    )

    response = client.patch(url(shift.id, foreign.id), json={"amount": "1"}, headers=auth_headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Ganho não encontrado"}


@pytest.mark.parametrize(
    "body", [{}, {"amount": "0"}, {"amount": "5", "earned_at": "2026-09-20T10:00:00"}]
)
def test_invalid_body_is_rejected(
    client: TestClient, auth_headers: dict[str, str], shift: Shift, body: dict
) -> None:
    assert client.post(url(shift.id), json=body, headers=auth_headers).status_code == 422


@pytest.mark.parametrize(
    ("method", "with_id"), [("post", False), ("get", False), ("patch", True), ("delete", True)]
)
def test_earnings_require_authentication(client: TestClient, method: str, with_id: bool) -> None:
    path = url(uuid.uuid4(), uuid.uuid4() if with_id else None)

    assert client.request(method, path, json={"amount": "5"}).status_code == 401
