from fastapi import APIRouter

from app.core.deps import CurrentUser, UserServiceDep
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def get_me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)


@router.patch("/me", response_model=UserResponse)
def update_me(data: UserUpdate, user: CurrentUser, service: UserServiceDep) -> UserResponse:
    return UserResponse.model_validate(service.update(user, data))
