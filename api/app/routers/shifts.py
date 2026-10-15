import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser, ShiftServiceDep
from app.core.openapi import errors
from app.models import Shift, ShiftStatus
from app.schemas.shift import (
    GpsGapResponse,
    GpsStatusResponse,
    ShiftListItem,
    ShiftListQuery,
    ShiftPage,
    ShiftResponse,
    ShiftStart,
    ShiftSummaryResponse,
    shift_fields,
)
from app.services.shift_service import ShiftDetail, stored_summary

router = APIRouter(prefix="/shifts", tags=["shifts"], responses=errors(401))


def to_response(detail: ShiftDetail) -> ShiftResponse:
    return ShiftResponse(
        **shift_fields(detail.shift),
        summary=ShiftSummaryResponse.from_summary(detail.summary),
        gps=GpsStatusResponse(
            last_point_at=detail.last_point_at,
            gaps=[GpsGapResponse.from_gap(gap) for gap in detail.gaps],
        ),
    )


def to_list_item(shift: Shift) -> ShiftListItem:
    finished = shift.status == ShiftStatus.FINISHED
    summary = ShiftSummaryResponse.from_summary(stored_summary(shift)) if finished else None
    return ShiftListItem(**shift_fields(shift), summary=summary)


@router.post(
    "",
    response_model=ShiftResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Iniciar expediente",
    responses=errors(404, 409, 422),
)
def start_shift(data: ShiftStart, user: CurrentUser, service: ShiftServiceDep) -> ShiftResponse:
    return to_response(service.start(user, data))


@router.get("", response_model=ShiftPage, summary="Listar expedientes")
def list_shifts(
    query: Annotated[ShiftListQuery, Query()], user: CurrentUser, service: ShiftServiceDep
) -> ShiftPage:
    result = service.list_for_user(
        user, query.date_from, query.date_to, query.tz, query.page, query.size
    )
    return ShiftPage(
        items=[to_list_item(shift) for shift in result.items],
        total=result.total,
        page=query.page,
        size=query.size,
    )


@router.get(
    "/current",
    response_model=ShiftResponse,
    summary="Expediente em andamento com lucro parcial",
    responses=errors(404),
)
def current_shift(user: CurrentUser, service: ShiftServiceDep) -> ShiftResponse:
    return to_response(service.current(user))


@router.get(
    "/{shift_id}",
    response_model=ShiftResponse,
    summary="Detalhar expediente",
    responses=errors(404),
)
def get_shift(shift_id: uuid.UUID, user: CurrentUser, service: ShiftServiceDep) -> ShiftResponse:
    return to_response(service.get(user, shift_id))


@router.post(
    "/{shift_id}/finish",
    response_model=ShiftResponse,
    summary="Encerrar expediente",
    responses=errors(404, 409),
)
def finish_shift(shift_id: uuid.UUID, user: CurrentUser, service: ShiftServiceDep) -> ShiftResponse:
    return to_response(service.finish(user, shift_id))
