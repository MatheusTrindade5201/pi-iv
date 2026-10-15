import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

EARTH_RADIUS_M = 6_371_000
MONEY = Decimal("0.01")
KILOMETERS = Decimal("0.001")


@dataclass(frozen=True)
class GpsPoint:
    recorded_at: datetime
    latitude: float
    longitude: float
    accuracy_m: float | None = None


@dataclass(frozen=True)
class CalculationParams:
    max_accuracy_m: float = 50
    max_speed_kmh: float = 150
    stationary_threshold_m: float = 15
    gap_threshold_s: int = 120
    idle_fuel_ml_per_s: Decimal = Decimal("0.04")
    reanchor_after_points: int = 3


@dataclass(frozen=True)
class TrackSummary:
    distance_m: float
    idle_seconds: float

    @property
    def distance_km(self) -> Decimal:
        return Decimal(str(self.distance_m)) / 1000


@dataclass(frozen=True)
class GpsGap:
    start: datetime
    end: datetime
    minutes: int


@dataclass(frozen=True)
class ShiftSummary:
    earnings_total: Decimal
    fuel_cost: Decimal
    profit: Decimal
    distance_km: Decimal
    duration_minutes: int
    idle_minutes: int
    profit_per_hour: Decimal | None
    profit_per_km: Decimal | None


def haversine_m(a: GpsPoint, b: GpsPoint) -> float:
    lat1, lat2 = math.radians(a.latitude), math.radians(b.latitude)
    d_lat = lat2 - lat1
    d_lon = math.radians(b.longitude - a.longitude)
    h = math.sin(d_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(d_lon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def filter_points(points: Iterable[GpsPoint], params: CalculationParams) -> list[GpsPoint]:
    valid: list[GpsPoint] = []
    # Pontos seguidos descartados como salto, mas coerentes entre si. Se forem
    # muitos, quem estava errado era a referência (ex.: primeiro ponto vindo do
    # cache do GPS, longe da rota): ela sai e esses pontos entram.
    rejected: list[GpsPoint] = []
    for point in sorted(points, key=lambda p: p.recorded_at):
        if point.accuracy_m is not None and point.accuracy_m > params.max_accuracy_m:
            continue
        if not valid or _speed_kmh(valid[-1], point) <= params.max_speed_kmh:
            valid.append(point)
            rejected = []
            continue
        if rejected and _speed_kmh(rejected[-1], point) > params.max_speed_kmh:
            rejected = []
        rejected.append(point)
        if len(rejected) >= params.reanchor_after_points:
            while valid and _speed_kmh(valid[-1], rejected[0]) > params.max_speed_kmh:
                valid.pop()
            valid.extend(rejected)
            rejected = []
    return valid


def summarize_track(points: Iterable[GpsPoint], params: CalculationParams) -> TrackSummary:
    valid = filter_points(points, params)
    distance_m = 0.0
    idle_seconds = 0.0
    for previous, current in zip(valid, valid[1:], strict=False):
        distance = haversine_m(previous, current)
        if distance >= params.stationary_threshold_m:
            distance_m += distance
        else:
            idle_seconds += (current.recorded_at - previous.recorded_at).total_seconds()
    return TrackSummary(distance_m=distance_m, idle_seconds=idle_seconds)


def fuel_liters(track: TrackSummary, kml: Decimal, idle_fuel_ml_per_s: Decimal) -> Decimal:
    moving = track.distance_km / kml
    idle = Decimal(str(track.idle_seconds)) * idle_fuel_ml_per_s / 1000
    return moving + idle


def find_gps_gaps(
    started_at: datetime, points: Iterable[GpsPoint], threshold_s: int
) -> list[GpsGap]:
    ordered = sorted(points, key=lambda p: p.recorded_at)
    if not ordered:
        return []
    instants = [started_at, *(point.recorded_at for point in ordered)]
    return [
        GpsGap(start=start, end=end, minutes=int((end - start).total_seconds() // 60))
        for start, end in zip(instants, instants[1:], strict=False)
        if (end - start).total_seconds() > threshold_s
    ]


def summarize_shift(
    started_at: datetime,
    ended_at: datetime,
    points: Sequence[GpsPoint],
    earnings: Iterable[Decimal],
    kml: Decimal,
    price_per_liter: Decimal,
    params: CalculationParams,
) -> ShiftSummary:
    track = summarize_track(points, params)
    earnings_total = sum(earnings, Decimal(0))
    fuel_cost = fuel_liters(track, kml, params.idle_fuel_ml_per_s) * price_per_liter
    profit = earnings_total - fuel_cost
    duration_minutes = max(int((ended_at - started_at).total_seconds() // 60), 0)
    distance_km = track.distance_km

    return ShiftSummary(
        earnings_total=_money(earnings_total),
        fuel_cost=_money(fuel_cost),
        profit=_money(profit),
        distance_km=distance_km.quantize(KILOMETERS, rounding=ROUND_HALF_UP),
        duration_minutes=duration_minutes,
        idle_minutes=round(track.idle_seconds / 60),
        profit_per_hour=per_hour(profit, duration_minutes),
        profit_per_km=per_km(profit, distance_km),
    )


def per_hour(value: Decimal, minutes: int) -> Decimal | None:
    # Divide por no mínimo 1 hora: abaixo disso mostra o valor feito, sem projetar.
    return _money(value * 60 / max(minutes, 60)) if minutes else None


def per_km(value: Decimal, distance_km: Decimal) -> Decimal | None:
    return _money(value / distance_km) if distance_km else None


def _speed_kmh(a: GpsPoint, b: GpsPoint) -> float:
    seconds = (b.recorded_at - a.recorded_at).total_seconds()
    if seconds <= 0:
        return math.inf
    return haversine_m(a, b) / seconds * 3.6


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)
