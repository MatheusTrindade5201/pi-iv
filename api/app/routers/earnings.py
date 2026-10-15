import uuid

from fastapi import APIRouter, Response, status

from app.core.deps import CurrentUser, EarningServiceDep
from app.core.openapi import errors
from app.schemas.earning import EarningCreate, EarningResponse, EarningUpdate

router = APIRouter(prefix="/shifts/{shift_id}/earnings", tags=["earnings"], responses=errors(401))


@router.post(
    "",
    response_model=EarningResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Lançar ganho",
    responses=errors(404, 409, 422),
)
def add_earning(
    shift_id: uuid.UUID, data: EarningCreate, user: CurrentUser, service: EarningServiceDep
) -> EarningResponse:
    return EarningResponse.model_validate(service.add(user, shift_id, data))


@router.get(
    "",
    response_model=list[EarningResponse],
    summary="Listar ganhos do expediente",
    responses=errors(404),
)
def list_earnings(
    shift_id: uuid.UUID, user: CurrentUser, service: EarningServiceDep
) -> list[EarningResponse]:
    return [EarningResponse.model_validate(e) for e in service.list_for_shift(user, shift_id)]


@router.patch(
    "/{earning_id}",
    response_model=EarningResponse,
    summary="Editar ganho (Sobrescrever ganho atual)",
    responses=errors(404, 409, 422),
)
def update_earning(
    shift_id: uuid.UUID,
    earning_id: uuid.UUID,
    data: EarningUpdate,
    user: CurrentUser,
    service: EarningServiceDep,
) -> EarningResponse:
    return EarningResponse.model_validate(service.update(user, shift_id, earning_id, data))


@router.delete(
    "/{earning_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover ganho",
    responses=errors(404, 409),
)
def delete_earning(
    shift_id: uuid.UUID, earning_id: uuid.UUID, user: CurrentUser, service: EarningServiceDep
) -> Response:
    service.delete(user, shift_id, earning_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
