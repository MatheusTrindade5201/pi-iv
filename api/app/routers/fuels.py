from fastapi import APIRouter

from app.core.deps import CurrentUser, FuelServiceDep
from app.schemas.fuel import FuelResponse

router = APIRouter(prefix="/fuels", tags=["fuels"])


@router.get("", response_model=list[FuelResponse])
def list_fuels(_: CurrentUser, service: FuelServiceDep) -> list[FuelResponse]:
    return [FuelResponse.model_validate(fuel) for fuel in service.list_fuels()]
