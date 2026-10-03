from collections.abc import Sequence
from datetime import UTC, datetime

from app.core.errors import UnprocessableError
from app.models import FLEX_ID, Fuel, FuelPrice, User
from app.repositories.fuel_price_repository import FuelPriceRepository
from app.repositories.fuel_repository import FuelRepository
from app.schemas.fuel import FuelPricesUpdate

FUEL_NOT_FOUND = "Combustível não encontrado"
FLEX_HAS_NO_PRICE = "Flex não tem preço próprio; informe Gasolina ou Etanol"


class FuelService:
    def __init__(
        self, fuel_repository: FuelRepository, price_repository: FuelPriceRepository
    ) -> None:
        self.fuel_repository = fuel_repository
        self.price_repository = price_repository

    def list_fuels(self) -> Sequence[Fuel]:
        return self.fuel_repository.list_all()

    def current_prices(self, user: User) -> Sequence[FuelPrice]:
        return self.price_repository.current_prices(user.id, datetime.now(UTC))

    def update_prices(self, user: User, data: FuelPricesUpdate) -> Sequence[FuelPrice]:
        fuel_ids = {item.fuel_id for item in data.prices}
        if FLEX_ID in fuel_ids:
            raise UnprocessableError(FLEX_HAS_NO_PRICE)
        if len(self.fuel_repository.get_by_ids(fuel_ids)) != len(fuel_ids):
            raise UnprocessableError(FUEL_NOT_FOUND)

        now = datetime.now(UTC)
        self.price_repository.add_all(
            FuelPrice(
                user_id=user.id,
                fuel_id=item.fuel_id,
                price_per_liter=item.price_per_liter,
                valid_from=now,
            )
            for item in data.prices
        )
        return self.price_repository.current_prices(user.id, now)
