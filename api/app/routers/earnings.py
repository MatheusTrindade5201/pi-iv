import uuid

from fastapi import APIRouter, Response, status

from app.core.deps import CurrentUser, EarningServiceDep
from app.schemas.earning import EarningCreate, EarningResponse, EarningUpdate

router = APIRouter(prefix="/shifts/{shift_id}/earnings", tags=["earnings"])


@router.post("", response_model=EarningResponse, status_code=status.HTTP_201_CREATED)
def add_earning(
    shift_id: uuid.UUID, data: EarningCreate, user: CurrentUser, service: EarningServiceDep
) -> EarningResponse:
    return EarningResponse.model_validate(service.add(user, shift_id, data))


@router.get("", response_model=list[EarningResponse])
def list_earnings(
    shift_id: uuid.UUID, user: CurrentUser, service: EarningServiceDep
) -> list[EarningResponse]:
    return [EarningResponse.model_validate(e) for e in service.list_for_shift(user, shift_id)]


@router.patch("/{earning_id}", response_model=EarningResponse)
def update_earning(
    shift_id: uuid.UUID,
    earning_id: uuid.UUID,
    data: EarningUpdate,
    user: CurrentUser,
    service: EarningServiceDep,
) -> EarningResponse:
    return EarningResponse.model_validate(service.update(user, shift_id, earning_id, data))


@router.delete("/{earning_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_earning(
    shift_id: uuid.UUID, earning_id: uuid.UUID, user: CurrentUser, service: EarningServiceDep
) -> Response:
    service.delete(user, shift_id, earning_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
