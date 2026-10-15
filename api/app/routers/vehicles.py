import uuid

from fastapi import APIRouter, Response, status

from app.core.deps import CurrentUser, VehicleServiceDep
from app.core.openapi import errors
from app.schemas.vehicle import VehicleCreate, VehicleResponse, VehicleUpdate

router = APIRouter(prefix="/vehicles", tags=["vehicles"], responses=errors(401))


@router.post(
    "",
    response_model=VehicleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar moto",
    responses=errors(422),
)
def create_vehicle(
    data: VehicleCreate, user: CurrentUser, service: VehicleServiceDep
) -> VehicleResponse:
    return VehicleResponse.from_model(service.create(user, data))


@router.get("", response_model=list[VehicleResponse], summary="Listar motos")
def list_vehicles(user: CurrentUser, service: VehicleServiceDep) -> list[VehicleResponse]:
    return [VehicleResponse.from_model(vehicle) for vehicle in service.list(user)]


@router.get(
    "/{vehicle_id}", response_model=VehicleResponse, summary="Detalhar moto", responses=errors(404)
)
def get_vehicle(
    vehicle_id: uuid.UUID, user: CurrentUser, service: VehicleServiceDep
) -> VehicleResponse:
    return VehicleResponse.from_model(service.get(user, vehicle_id))


@router.patch(
    "/{vehicle_id}",
    response_model=VehicleResponse,
    summary="Atualizar moto",
    responses=errors(404, 422),
)
def update_vehicle(
    vehicle_id: uuid.UUID, data: VehicleUpdate, user: CurrentUser, service: VehicleServiceDep
) -> VehicleResponse:
    return VehicleResponse.from_model(service.update(user, vehicle_id, data))


@router.delete(
    "/{vehicle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Excluir moto",
    responses=errors(404, 409),
)
def delete_vehicle(
    vehicle_id: uuid.UUID, user: CurrentUser, service: VehicleServiceDep
) -> Response:
    service.delete(user, vehicle_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
