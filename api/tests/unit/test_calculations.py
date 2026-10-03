from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.services.calculations import (
    CalculationParams,
    GpsPoint,
    filter_points,
    find_gps_gaps,
    haversine_m,
    per_hour,
    per_km,
    summarize_shift,
    summarize_track,
)

pytestmark = pytest.mark.unit

T0 = datetime(2026, 9, 20, 10, 0, tzinfo=UTC)
METERS_PER_DEGREE = 111_194.926644
PARAMS = CalculationParams()


def point(seconds: float, east_m: float = 0, accuracy_m: float | None = None) -> GpsPoint:
    return GpsPoint(
        recorded_at=T0 + timedelta(seconds=seconds),
        latitude=0.0,
        longitude=east_m / METERS_PER_DEGREE,
        accuracy_m=accuracy_m,
    )


def summary(points: list[GpsPoint], earnings: list[str], minutes: float, **kwargs: object):
    return summarize_shift(
        started_at=T0,
        ended_at=T0 + timedelta(minutes=minutes),
        points=points,
        earnings=[Decimal(value) for value in earnings],
        kml=kwargs.get("kml", Decimal("32")),
        price_per_liter=kwargs.get("price", Decimal("6.00")),
        params=PARAMS,
    )


def test_haversine_one_degree_of_longitude_on_equator() -> None:
    a = GpsPoint(T0, 0.0, 0.0)
    b = GpsPoint(T0, 0.0, 1.0)

    assert haversine_m(a, b) == pytest.approx(111_194.93, abs=0.01)


def test_haversine_known_city_distance() -> None:
    se = GpsPoint(T0, -23.550520, -46.633308)
    masp = GpsPoint(T0, -23.561414, -46.655881)

    assert haversine_m(se, masp) == pytest.approx(2_600, rel=0.02)


def test_filter_points_sorts_by_time() -> None:
    late, early = point(60, 100), point(0)

    assert filter_points([late, early], PARAMS) == [early, late]


def test_filter_points_discards_low_accuracy() -> None:
    good, bad, unknown = point(0, accuracy_m=10), point(10, accuracy_m=60), point(20)

    assert filter_points([good, bad, unknown], PARAMS) == [good, unknown]


def test_filter_points_discards_impossible_jump() -> None:
    start = point(0)
    jump = point(60, east_m=10_000)
    back = point(120, east_m=100)

    assert filter_points([start, jump, back], PARAMS) == [start, back]


@pytest.mark.parametrize(("east_m", "distance_m", "idle_seconds"), [(14.9, 0, 30), (15.1, 15.1, 0)])
def test_stationary_threshold(east_m: float, distance_m: float, idle_seconds: float) -> None:
    track = summarize_track([point(0), point(30, east_m)], PARAMS)

    assert track.distance_m == pytest.approx(distance_m, abs=0.01)
    assert track.idle_seconds == idle_seconds


def test_long_gap_without_moving_counts_as_idle() -> None:
    track = summarize_track([point(0, 500), point(40 * 60, 505)], PARAMS)

    assert track.idle_seconds == 40 * 60
    assert track.distance_m == 0


def test_long_gap_while_moving_counts_distance() -> None:
    track = summarize_track([point(0), point(30 * 60, 1_000)], PARAMS)

    assert track.distance_m == pytest.approx(1_000, abs=0.01)
    assert track.idle_seconds == 0


def test_summary_combines_moving_and_idle_fuel() -> None:
    points = [point(0), point(3600, 32_000), point(4200, 32_000)]

    result = summary(points, ["50.00"], minutes=70, kml=Decimal("32"), price=Decimal("6.00"))

    assert result.distance_km == Decimal("32.000")
    assert result.idle_minutes == 10
    assert result.fuel_cost == Decimal("6.14")
    assert result.earnings_total == Decimal("50.00")
    assert result.profit == Decimal("43.86")
    assert result.duration_minutes == 70
    assert result.profit_per_hour == Decimal("37.59")
    assert result.profit_per_km == Decimal("1.37")


def test_profit_can_be_negative() -> None:
    result = summary([point(0), point(3600, 32_000)], [], minutes=60)

    assert result.profit == Decimal("-6.00")
    assert result.profit_per_hour == Decimal("-6.00")


def test_mock_values_from_prototype() -> None:
    result = summary([], ["245.00"], minutes=240)

    assert result.earnings_total == Decimal("245.00")
    assert result.profit_per_hour == Decimal("61.25")
    assert summary([], ["187.40"], minutes=240).profit_per_hour == Decimal("46.85")


def test_zero_duration_and_distance_have_no_rates() -> None:
    result = summary([], ["10.00"], minutes=0)

    assert result.duration_minutes == 0
    assert result.profit_per_hour is None
    assert result.profit_per_km is None
    assert result.distance_km == Decimal("0.000")


def test_duration_is_truncated_to_whole_minutes() -> None:
    assert summary([], [], minutes=59.99).duration_minutes == 59


def test_rounding_is_half_up() -> None:
    assert summary([], ["0.25"], minutes=120).profit_per_hour == Decimal("0.13")


def test_gps_gaps_from_start_and_between_points() -> None:
    gaps = find_gps_gaps(T0, [point(240), point(180), point(10 * 60)], threshold_s=120)

    assert [(gap.start, gap.end, gap.minutes) for gap in gaps] == [
        (T0, T0 + timedelta(minutes=3), 3),
        (T0 + timedelta(minutes=4), T0 + timedelta(minutes=10), 6),
    ]


def test_no_points_means_no_gaps() -> None:
    assert find_gps_gaps(T0, [], threshold_s=120) == []


def test_filter_points_discards_point_with_same_timestamp() -> None:
    first = point(0)

    assert filter_points([first, point(0, east_m=50)], PARAMS) == [first]


@pytest.mark.parametrize(
    ("value", "minutes", "expected"),
    [
        (Decimal("187.40"), 240, Decimal("46.85")),
        (Decimal("0.25"), 120, Decimal("0.13")),
        (Decimal("-10.00"), 60, Decimal("-10.00")),
        (Decimal("10.00"), 0, None),
    ],
)
def test_per_hour(value: Decimal, minutes: int, expected: Decimal | None) -> None:
    assert per_hour(value, minutes) == expected


@pytest.mark.parametrize(
    ("value", "km", "expected"),
    [
        (Decimal("187.40"), Decimal("78.2"), Decimal("2.40")),
        (Decimal("10.00"), Decimal("0"), None),
    ],
)
def test_per_km(value: Decimal, km: Decimal, expected: Decimal | None) -> None:
    assert per_km(value, km) == expected
