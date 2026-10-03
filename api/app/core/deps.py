from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError

from app.core.config import Settings
from app.core.db import DbSession
from app.core.errors import UnauthorizedError
from app.core.security import decode_access_token
from app.models import User
from app.repositories.fuel_price_repository import FuelPriceRepository
from app.repositories.fuel_repository import FuelRepository
from app.repositories.user_repository import UserRepository
from app.repositories.vehicle_repository import VehicleRepository
from app.services.auth_service import AuthService
from app.services.fuel_service import FuelService
from app.services.user_service import UserService
from app.services.vehicle_service import VehicleService

NOT_AUTHENTICATED = "Não autenticado"

bearer_scheme = HTTPBearer(auto_error=False)


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


AppSettings = Annotated[Settings, Depends(get_app_settings)]


def get_user_repository(db: DbSession) -> UserRepository:
    return UserRepository(db)


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]


def get_auth_service(repository: UserRepositoryDep, settings: AppSettings) -> AuthService:
    return AuthService(repository, settings)


def get_user_service(repository: UserRepositoryDep) -> UserService:
    return UserService(repository)


def get_fuel_service(db: DbSession) -> FuelService:
    return FuelService(FuelRepository(db), FuelPriceRepository(db))


def get_vehicle_service(db: DbSession) -> VehicleService:
    return VehicleService(VehicleRepository(db), FuelRepository(db))


def get_current_user(
    repository: UserRepositoryDep,
    settings: AppSettings,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None:
        raise UnauthorizedError(NOT_AUTHENTICATED)
    try:
        user_id = decode_access_token(credentials.credentials, settings)
    except InvalidTokenError as exc:
        raise UnauthorizedError(NOT_AUTHENTICATED) from exc

    user = repository.get_by_id(user_id)
    if user is None:
        raise UnauthorizedError(NOT_AUTHENTICATED)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
FuelServiceDep = Annotated[FuelService, Depends(get_fuel_service)]
VehicleServiceDep = Annotated[VehicleService, Depends(get_vehicle_service)]
