import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError

from app.core.errors import ConflictError, NotFoundError, UnprocessableError
from app.models import ETHANOL_ID, FLEX_ID, GASOLINE_ID, Shift, ShiftStatus, TrackPoint, User
from app.repositories.earning_repository import EarningRepository
from app.repositories.fuel_price_repository import FuelPriceRepository
from app.repositories.shift_repository import ShiftRepository
from app.repositories.track_point_repository import TrackPointRepository
from app.repositories.vehicle_repository import VehicleRepository
from app.schemas.shift import ShiftStart
from app.services.calculations import (
    CalculationParams,
    GpsGap,
    GpsPoint,
    ShiftSummary,
    find_gps_gaps,
    summarize_shift,
)
from app.services.shift_access import get_open_shift, get_user_shift

VEHICLE_NOT_FOUND = "Veículo não encontrado"
NO_SHIFT_IN_PROGRESS = "Nenhum expediente em andamento"
SHIFT_ALREADY_IN_PROGRESS = "Já existe um expediente em andamento"
FUEL_PRICE_MISSING = "Cadastre o preço do combustível antes de iniciar"
FLEX_FUEL_REQUIRED = "Informe o combustível abastecido (Gasolina ou Etanol) para moto Flex"
FUEL_MISMATCH = "Combustível diferente do cadastrado no veículo"

FLEX_OPTIONS = {GASOLINE_ID, ETHANOL_ID}


@dataclass(frozen=True)
class ShiftDetail:
    shift: Shift
    summary: ShiftSummary
    last_point_at: datetime | None
    gaps: list[GpsGap]


@dataclass(frozen=True)
class ShiftListResult:
    items: Sequence[Shift]
    total: int


class ShiftService:
    def __init__(
        self,
        shifts: ShiftRepository,
        vehicles: VehicleRepository,
        prices: FuelPriceRepository,
        earnings: EarningRepository,
        track_points: TrackPointRepository,
        params: CalculationParams,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.shifts = shifts
        self.vehicles = vehicles
        self.prices = prices
        self.earnings = earnings
        self.track_points = track_points
        self.params = params
        self.clock = clock

    def start(self, user: User, data: ShiftStart) -> ShiftDetail:
        vehicle = self.vehicles.get_for_user(data.vehicle_id, user.id)
        if vehicle is None:
            raise NotFoundError(VEHICLE_NOT_FOUND)
        fuel_id = self._fuel_used(vehicle.fuel_id, data.fuel_id)

        if self.shifts.get_in_progress(user.id) is not None:
            raise ConflictError(SHIFT_ALREADY_IN_PROGRESS)

        now = self.clock()
        price = self.prices.current_price(user.id, fuel_id, now)
        if price is None:
            raise ConflictError(FUEL_PRICE_MISSING)

        shift = Shift(
            user_id=user.id,
            vehicle_id=vehicle.id,
            fuel_id=fuel_id,
            started_at=now,
            status=ShiftStatus.IN_PROGRESS,
            price_per_liter_used=price.price_per_liter,
            kml_used=vehicle.declared_kml,
        )
        try:
            shift = self.shifts.save(shift)
        except IntegrityError as exc:
            self.shifts.rollback()
            raise ConflictError(SHIFT_ALREADY_IN_PROGRESS) from exc
        return self._detail(shift)

    def current(self, user: User) -> ShiftDetail:
        shift = self.shifts.get_in_progress(user.id)
        if shift is None:
            raise NotFoundError(NO_SHIFT_IN_PROGRESS)
        return self._detail(shift)

    def get(self, user: User, shift_id: uuid.UUID) -> ShiftDetail:
        return self._detail(get_user_shift(self.shifts, user, shift_id))

    def finish(self, user: User, shift_id: uuid.UUID) -> ShiftDetail:
        shift = get_open_shift(self.shifts, user, shift_id)
        ended_at = self.clock()
        points = self._points(shift)
        summary = self._summarize(shift, points, ended_at)

        shift.ended_at = ended_at
        shift.status = ShiftStatus.FINISHED
        shift.distance_km = summary.distance_km
        shift.idle_minutes = summary.idle_minutes
        shift.fuel_cost = summary.fuel_cost
        shift.earnings_total = summary.earnings_total
        shift.profit = summary.profit
        shift.duration_minutes = summary.duration_minutes
        shift.profit_per_hour = summary.profit_per_hour
        shift.profit_per_km = summary.profit_per_km
        shift = self.shifts.save(shift)
        return self._build_detail(shift, summary, points)

    def list_for_user(
        self,
        user: User,
        date_from: date | None,
        date_to: date | None,
        tz: str,
        page: int,
        size: int,
    ) -> ShiftListResult:
        zone = ZoneInfo(tz)
        start = _local_midnight(date_from, zone) if date_from else None
        end = _local_midnight(date_to + timedelta(days=1), zone) if date_to else None
        items, total = self.shifts.list_for_user(user.id, start, end, (page - 1) * size, size)
        return ShiftListResult(items=items, total=total)

    def _fuel_used(self, vehicle_fuel_id: uuid.UUID, requested: uuid.UUID | None) -> uuid.UUID:
        if vehicle_fuel_id == FLEX_ID:
            if requested not in FLEX_OPTIONS:
                raise UnprocessableError(FLEX_FUEL_REQUIRED)
            return requested
        if requested is not None and requested != vehicle_fuel_id:
            raise UnprocessableError(FUEL_MISMATCH)
        return vehicle_fuel_id

    def _detail(self, shift: Shift) -> ShiftDetail:
        points = self._points(shift)
        if shift.status == ShiftStatus.FINISHED:
            summary = stored_summary(shift)
        else:
            summary = self._summarize(shift, points, self.clock())
        return self._build_detail(shift, summary, points)

    def _build_detail(
        self, shift: Shift, summary: ShiftSummary, points: list[GpsPoint]
    ) -> ShiftDetail:
        return ShiftDetail(
            shift=shift,
            summary=summary,
            last_point_at=points[-1].recorded_at if points else None,
            gaps=find_gps_gaps(shift.started_at, points, self.params.gap_threshold_s),
        )

    def _summarize(self, shift: Shift, points: list[GpsPoint], until: datetime) -> ShiftSummary:
        earnings = [earning.amount for earning in self.earnings.list_for_shift(shift.id)]
        return summarize_shift(
            started_at=shift.started_at,
            ended_at=until,
            points=points,
            earnings=earnings,
            kml=shift.kml_used,
            price_per_liter=shift.price_per_liter_used,
            params=self.params,
        )

    def _points(self, shift: Shift) -> list[GpsPoint]:
        return [to_gps_point(point) for point in self.track_points.list_for_shift(shift.id)]


def to_gps_point(point: TrackPoint) -> GpsPoint:
    return GpsPoint(
        recorded_at=point.recorded_at,
        latitude=float(point.latitude),
        longitude=float(point.longitude),
        accuracy_m=float(point.accuracy_m) if point.accuracy_m is not None else None,
    )


def stored_summary(shift: Shift) -> ShiftSummary:
    return ShiftSummary(
        earnings_total=shift.earnings_total,
        fuel_cost=shift.fuel_cost,
        profit=shift.profit,
        distance_km=shift.distance_km,
        duration_minutes=shift.duration_minutes,
        idle_minutes=shift.idle_minutes,
        profit_per_hour=shift.profit_per_hour,
        profit_per_km=shift.profit_per_km,
    )


def _local_midnight(day: date, zone: ZoneInfo) -> datetime:
    return datetime.combine(day, time.min, tzinfo=zone).astimezone(UTC)
