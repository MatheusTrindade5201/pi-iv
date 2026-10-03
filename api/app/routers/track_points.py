import uuid

from fastapi import APIRouter, status

from app.core.deps import CurrentUser, TrackPointServiceDep
from app.schemas.track_point import TrackPointBatch, TrackPointBatchResult, TrackPointResponse

router = APIRouter(prefix="/shifts/{shift_id}/track-points", tags=["track-points"])


@router.post("", response_model=TrackPointBatchResult, status_code=status.HTTP_202_ACCEPTED)
def add_track_points(
    shift_id: uuid.UUID, data: TrackPointBatch, user: CurrentUser, service: TrackPointServiceDep
) -> TrackPointBatchResult:
    result = service.add_batch(user, shift_id, data)
    return TrackPointBatchResult(
        accepted=result.accepted, duplicated=result.duplicated, rejected=result.rejected
    )


@router.get("", response_model=list[TrackPointResponse])
def list_track_points(
    shift_id: uuid.UUID, user: CurrentUser, service: TrackPointServiceDep
) -> list[TrackPointResponse]:
    return [TrackPointResponse.model_validate(p) for p in service.list_for_shift(user, shift_id)]
