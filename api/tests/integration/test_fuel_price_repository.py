from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models import ETHANOL_ID, GASOLINE_ID
from app.repositories.fuel_price_repository import FuelPriceRepository
from tests.factories import make_fuel_price, make_user

pytestmark = pytest.mark.integration

NOW = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


def test_current_price_respects_valid_from(db_session: Session) -> None:
    user = make_user(db_session)
    make_fuel_price(db_session, user, price_per_liter=Decimal("6.000"), valid_from=NOW)
    make_fuel_price(
        db_session, user, price_per_liter=Decimal("6.500"), valid_from=NOW + timedelta(days=2)
    )
    repository = FuelPriceRepository(db_session)

    before_first = repository.current_price(user.id, GASOLINE_ID, NOW - timedelta(seconds=1))
    between = repository.current_price(user.id, GASOLINE_ID, NOW + timedelta(days=1))
    after_second = repository.current_price(user.id, GASOLINE_ID, NOW + timedelta(days=3))

    assert before_first is None
    assert between is not None and between.price_per_liter == Decimal("6.000")
    assert after_second is not None and after_second.price_per_liter == Decimal("6.500")


def test_current_prices_returns_latest_per_fuel(db_session: Session) -> None:
    user = make_user(db_session)
    make_fuel_price(db_session, user, price_per_liter=Decimal("6.000"), valid_from=NOW)
    make_fuel_price(
        db_session, user, price_per_liter=Decimal("6.500"), valid_from=NOW + timedelta(hours=1)
    )
    make_fuel_price(
        db_session, user, fuel_id=ETHANOL_ID, price_per_liter=Decimal("3.750"), valid_from=NOW
    )

    prices = FuelPriceRepository(db_session).current_prices(user.id, NOW + timedelta(days=1))

    assert {price.fuel.name: price.price_per_liter for price in prices} == {
        "Gasolina": Decimal("6.500"),
        "Etanol": Decimal("3.750"),
    }
