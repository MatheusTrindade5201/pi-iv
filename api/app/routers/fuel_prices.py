from fastapi import APIRouter

from app.core.deps import CurrentUser, FuelServiceDep
from app.schemas.fuel import FuelPriceResponse, FuelPricesUpdate

router = APIRouter(prefix="/fuel-prices", tags=["fuel-prices"])


@router.get("/current", response_model=list[FuelPriceResponse])
def current_prices(user: CurrentUser, service: FuelServiceDep) -> list[FuelPriceResponse]:
    return [FuelPriceResponse.from_model(price) for price in service.current_prices(user)]


@router.put("", response_model=list[FuelPriceResponse])
def update_prices(
    data: FuelPricesUpdate, user: CurrentUser, service: FuelServiceDep
) -> list[FuelPriceResponse]:
    return [FuelPriceResponse.from_model(price) for price in service.update_prices(user, data)]
