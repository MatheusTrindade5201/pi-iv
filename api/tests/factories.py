import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import (
    GASOLINE_ID,
    Earning,
    FuelPrice,
    Shift,
    ShiftStatus,
    TrackPoint,
    User,
    Vehicle,
)


def make_user(session: Session, password: str | None = None, **overrides) -> User:
    data = {
        "name": "John Doe",
        "email": f"user-{uuid.uuid4().hex[:8]}@example.com",
        "password_hash": hash_password(password) if password else "not-a-real-hash",
    }
    user = User(**(data | overrides))
    session.add(user)
    session.flush()
    return user


def make_vehicle(session: Session, user: User, **overrides) -> Vehicle:
    data = {
        "user_id": user.id,
        "fuel_id": GASOLINE_ID,
        "model": "Honda CG 160",
        "declared_kml": Decimal("32.00"),
    }
    vehicle = Vehicle(**(data | overrides))
    session.add(vehicle)
    session.flush()
    return vehicle


def make_fuel_price(session: Session, user: User, **overrides) -> FuelPrice:
    data = {
        "user_id": user.id,
        "fuel_id": GASOLINE_ID,
        "price_per_liter": Decimal("6.200"),
        "valid_from": datetime.now(UTC),
    }
    price = FuelPrice(**(data | overrides))
    session.add(price)
    session.flush()
    return price


def make_shift(session: Session, user: User, vehicle: Vehicle, **overrides) -> Shift:
    data = {
        "user_id": user.id,
        "vehicle_id": vehicle.id,
        "fuel_id": vehicle.fuel_id,
        "started_at": datetime.now(UTC),
        "status": ShiftStatus.IN_PROGRESS,
        "price_per_liter_used": Decimal("6.200"),
        "kml_used": vehicle.declared_kml,
    }
    shift = Shift(**(data | overrides))
    session.add(shift)
    session.flush()
    return shift


def make_earning(session: Session, shift: Shift, **overrides) -> Earning:
    data = {"shift_id": shift.id, "amount": Decimal("20.00"), "earned_at": datetime.now(UTC)}
    earning = Earning(**(data | overrides))
    session.add(earning)
    session.flush()
    return earning


def make_track_point(session: Session, shift: Shift, **overrides) -> TrackPoint:
    data = {
        "shift_id": shift.id,
        "recorded_at": datetime.now(UTC),
        "latitude": Decimal("-23.550520"),
        "longitude": Decimal("-46.633308"),
    }
    point = TrackPoint(**(data | overrides))
    session.add(point)
    session.flush()
    return point
