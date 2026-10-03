from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.track_point import TrackPointBatch, TrackPointInput

pytestmark = pytest.mark.unit

RECORDED_AT = "2026-09-20T13:00:00Z"


def point_data(**overrides: object) -> dict[str, object]:
    return {"recorded_at": RECORDED_AT, "latitude": -23.55052, "longitude": -46.633308} | overrides


def test_coordinates_are_rounded_to_six_places() -> None:
    point = TrackPointInput(
        **point_data(
            latitude=-23.5505204999, longitude=-46.6333085, accuracy_m=8.456, speed_ms=11.234
        )
    )

    assert point.latitude == Decimal("-23.550520")
    assert point.longitude == Decimal("-46.633309")
    assert point.accuracy_m == Decimal("8.46")
    assert point.speed_ms == Decimal("11.23")


def test_optional_fields_default_to_none() -> None:
    point = TrackPointInput(**point_data())

    assert point.accuracy_m is None
    assert point.speed_ms is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"latitude": 90.1},
        {"latitude": -91},
        {"longitude": 180.5},
        {"accuracy_m": -1},
        {"accuracy_m": 100000},
        {"speed_ms": -0.5},
        {"recorded_at": "2026-09-20T13:00:00"},
    ],
)
def test_invalid_point_is_rejected(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        TrackPointInput(**point_data(**overrides))


@pytest.mark.parametrize("size", [0, 501])
def test_batch_size_limits(size: int) -> None:
    with pytest.raises(ValidationError):
        TrackPointBatch(points=[point_data()] * size)


def test_batch_with_500_points_is_valid() -> None:
    assert len(TrackPointBatch(points=[point_data()] * 500).points) == 500
