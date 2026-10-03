import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Shift, TrackPoint, User
from tests.factories import make_shift, make_user, make_vehicle

pytestmark = pytest.mark.integration

SE = (-23.550520, -46.633308)
MASP = (-23.561414, -46.655881)


@pytest.fixture
def shift(db_session: Session, user: User) -> Shift:
    return make_shift(
        db_session,
        user,
        make_vehicle(db_session, user),
        started_at=datetime.now(UTC) - timedelta(hours=2),
    )


def url(shift_id: uuid.UUID) -> str:
    return f"/api/v1/shifts/{shift_id}/track-points"


def points(shift: Shift, *items: tuple[int, tuple[float, float]]) -> dict:
    return {
        "points": [
            {
                "recorded_at": (shift.started_at + timedelta(minutes=minute)).isoformat(),
                "latitude": lat,
                "longitude": lon,
                "accuracy_m": 8,
            }
            for minute, (lat, lon) in items
        ]
    }


def stored_count(db_session: Session, shift: Shift) -> int:
    return db_session.scalar(
        select(func.count()).select_from(TrackPoint).where(TrackPoint.shift_id == shift.id)
    )


def test_batch_is_accepted(
    client: TestClient, auth_headers: dict[str, str], shift: Shift, db_session: Session
) -> None:
    response = client.post(
        url(shift.id), json=points(shift, (5, SE), (20, MASP), (30, MASP)), headers=auth_headers
    )

    assert response.status_code == 202
    assert response.json() == {"accepted": 3, "duplicated": 0, "rejected": 0}
    assert stored_count(db_session, shift) == 3


def test_resending_batch_does_not_duplicate(
    client: TestClient, auth_headers: dict[str, str], shift: Shift, db_session: Session
) -> None:
    payload = points(shift, (5, SE), (20, MASP))
    client.post(url(shift.id), json=payload, headers=auth_headers)

    again = client.post(url(shift.id), json=payload, headers=auth_headers)
    overlap = client.post(
        url(shift.id), json=points(shift, (20, MASP), (30, MASP)), headers=auth_headers
    )

    assert again.json() == {"accepted": 0, "duplicated": 2, "rejected": 0}
    assert overlap.json() == {"accepted": 1, "duplicated": 1, "rejected": 0}
    assert stored_count(db_session, shift) == 3


def test_points_feed_current_summary(
    client: TestClient, auth_headers: dict[str, str], shift: Shift
) -> None:
    client.post(
        url(shift.id), json=points(shift, (5, SE), (20, MASP), (30, MASP)), headers=auth_headers
    )

    current = client.get("/api/v1/shifts/current", headers=auth_headers).json()

    assert 2.4 < float(current["summary"]["distance_km"]) < 2.8
    assert current["summary"]["idle_minutes"] == 10
    assert current["gps"]["last_point_at"].startswith(
        (shift.started_at + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M")
    )
    assert [gap["minutes"] for gap in current["gps"]["gaps"]] == [5, 15, 10]


def test_points_outside_shift_are_rejected(
    client: TestClient, auth_headers: dict[str, str], shift: Shift
) -> None:
    response = client.post(
        url(shift.id), json=points(shift, (-10, SE), (5, SE), (600, SE)), headers=auth_headers
    )

    assert response.json() == {"accepted": 1, "duplicated": 0, "rejected": 2}


def test_batch_with_only_rejected_points(
    client: TestClient, auth_headers: dict[str, str], shift: Shift, db_session: Session
) -> None:
    response = client.post(url(shift.id), json=points(shift, (-10, SE)), headers=auth_headers)

    assert response.json() == {"accepted": 0, "duplicated": 0, "rejected": 1}
    assert stored_count(db_session, shift) == 0


def test_list_points_in_chronological_order(
    client: TestClient, auth_headers: dict[str, str], shift: Shift
) -> None:
    client.post(url(shift.id), json=points(shift, (20, MASP), (5, SE)), headers=auth_headers)

    response = client.get(url(shift.id), headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert [(p["latitude"], p["longitude"]) for p in body] == [
        ("-23.550520", "-46.633308"),
        ("-23.561414", "-46.655881"),
    ]
    assert body[0]["accuracy_m"] == "8.00"
    assert body[0]["speed_ms"] is None


def test_finished_shift_rejects_points(
    client: TestClient, auth_headers: dict[str, str], shift: Shift
) -> None:
    client.post(f"/api/v1/shifts/{shift.id}/finish", headers=auth_headers)

    response = client.post(url(shift.id), json=points(shift, (5, SE)), headers=auth_headers)

    assert response.status_code == 409
    assert response.json() == {"detail": "Expediente já encerrado"}
    assert client.get(url(shift.id), headers=auth_headers).status_code == 200


def test_shift_of_other_user_returns_404(
    client: TestClient, auth_headers: dict[str, str], db_session: Session
) -> None:
    other = make_user(db_session)
    other_shift = make_shift(db_session, other, make_vehicle(db_session, other))

    post = client.post(url(other_shift.id), json=points(other_shift, (1, SE)), headers=auth_headers)
    get = client.get(url(other_shift.id), headers=auth_headers)

    assert (post.status_code, get.status_code) == (404, 404)


@pytest.mark.parametrize(
    "body",
    [
        {"points": []},
        {"points": [{"recorded_at": "2026-09-20T10:00:00", "latitude": 0, "longitude": 0}]},
        {"points": [{"recorded_at": "2026-09-20T10:00:00Z", "latitude": 95, "longitude": 0}]},
    ],
)
def test_invalid_batch_is_rejected(
    client: TestClient, auth_headers: dict[str, str], shift: Shift, body: dict
) -> None:
    assert client.post(url(shift.id), json=body, headers=auth_headers).status_code == 422


@pytest.mark.parametrize("method", ["post", "get"])
def test_track_points_require_authentication(client: TestClient, method: str) -> None:
    assert client.request(method, url(uuid.uuid4()), json={"points": []}).status_code == 401
