from fastapi import APIRouter

from app.core.deps import CurrentUser, FuelServiceDep
from app.core.openapi import errors
from app.schemas.fuel import FuelResponse

router = APIRouter(prefix="/fuels", tags=["fuels"], responses=errors(401))


@router.get("", response_model=list[FuelResponse], summary="Listar combustíveis")
def list_fuels(_: CurrentUser, service: FuelServiceDep) -> list[FuelResponse]:
    return [FuelResponse.model_validate(fuel) for fuel in service.list_fuels()]
