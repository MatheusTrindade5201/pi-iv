from fastapi import APIRouter, status

from app.core.deps import AuthServiceDep
from app.core.openapi import errors
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar usuário",
    responses=errors(409),
)
def register(data: RegisterRequest, service: AuthServiceDep) -> UserResponse:
    return UserResponse.model_validate(service.register(data))


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Entrar e obter token JWT",
    responses=errors(401),
)
def login(data: LoginRequest, service: AuthServiceDep) -> TokenResponse:
    return TokenResponse(access_token=service.authenticate(data.email, data.password))
