from fastapi import APIRouter

from app.core.deps import CurrentUser, UserServiceDep
from app.core.openapi import errors
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"], responses=errors(401))


@router.get("/me", response_model=UserResponse, summary="Dados do usuário logado")
def get_me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)


@router.patch("/me", response_model=UserResponse, summary="Atualizar nome")
def update_me(data: UserUpdate, user: CurrentUser, service: UserServiceDep) -> UserResponse:
    return UserResponse.model_validate(service.update(user, data))
