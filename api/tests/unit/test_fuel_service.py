import uuid
from collections.abc import Collection, Iterable
from datetime import datetime
from decimal import Decimal

import pytest

from app.core.errors import UnprocessableError
from app.models import ETHANOL_ID, FLEX_ID, GASOLINE_ID, Fuel, FuelPrice, User
from app.models.fuel import SEED_FUELS
from app.schemas.fuel import FuelPricesUpdate
from app.services.fuel_service import FuelService

pytestmark = pytest.mark.unit


class FakeFuelRepository:
    def __init__(self) -> None:
        self.fuels = [Fuel(id=fuel_id, name=name) for fuel_id, name in SEED_FUELS.items()]

    def list_all(self) -> list[Fuel]:
        return self.fuels

    def get_by_ids(self, fuel_ids: Collection[uuid.UUID]) -> list[Fuel]:
        return [fuel for fuel in self.fuels if fuel.id in fuel_ids]


class FakeFuelPriceRepository:
    def __init__(self) -> None:
        self.prices: list[FuelPrice] = []

    def current_prices(self, user_id: uuid.UUID, at: datetime) -> list[FuelPrice]:
        latest: dict[uuid.UUID, FuelPrice] = {}
        for price in self.prices:
            if price.user_id != user_id or price.valid_from > at:
                continue
            current = latest.get(price.fuel_id)
            if current is None or price.valid_from > current.valid_from:
                latest[price.fuel_id] = price
        return list(latest.values())

    def add_all(self, prices: Iterable[FuelPrice]) -> None:
        self.prices.extend(prices)


@pytest.fixture
def price_repository() -> FakeFuelPriceRepository:
    return FakeFuelPriceRepository()


@pytest.fixture
def service(price_repository: FakeFuelPriceRepository) -> FuelService:
    return FuelService(FakeFuelRepository(), price_repository)


@pytest.fixture
def user() -> User:
    return User(id=uuid.uuid4(), name="John", email="john@example.com", password_hash="x")


def update(*items: tuple[uuid.UUID, str]) -> FuelPricesUpdate:
    return FuelPricesUpdate(
        prices=[{"fuel_id": fuel_id, "price_per_liter": price} for fuel_id, price in items]
    )


def test_list_fuels_returns_seed(service: FuelService) -> None:
    assert [fuel.name for fuel in service.list_fuels()] == ["Gasolina", "Etanol", "Flex"]


def test_update_prices_creates_one_price_per_item_with_same_valid_from(
    service: FuelService, price_repository: FakeFuelPriceRepository, user: User
) -> None:
    current = service.update_prices(user, update((GASOLINE_ID, "6.20"), (ETHANOL_ID, "3.75")))

    assert len(price_repository.prices) == 2
    assert len({price.valid_from for price in price_repository.prices}) == 1
    assert {price.fuel_id: price.price_per_liter for price in current} == {
        GASOLINE_ID: Decimal("6.20"),
        ETHANOL_ID: Decimal("3.75"),
    }


def test_update_prices_returns_all_current_prices(service: FuelService, user: User) -> None:
    service.update_prices(user, update((GASOLINE_ID, "6.20"), (ETHANOL_ID, "3.75")))

    current = service.update_prices(user, update((GASOLINE_ID, "6.40")))

    assert {price.fuel_id: price.price_per_liter for price in current} == {
        GASOLINE_ID: Decimal("6.40"),
        ETHANOL_ID: Decimal("3.75"),
    }


def test_flex_price_is_rejected(
    service: FuelService, price_repository: FakeFuelPriceRepository, user: User
) -> None:
    with pytest.raises(UnprocessableError, match="Flex"):
        service.update_prices(user, update((FLEX_ID, "5.00")))
    assert price_repository.prices == []


def test_unknown_fuel_is_rejected(service: FuelService, user: User) -> None:
    with pytest.raises(UnprocessableError, match="Combustível não encontrado"):
        service.update_prices(user, update((uuid.uuid4(), "5.00")))
