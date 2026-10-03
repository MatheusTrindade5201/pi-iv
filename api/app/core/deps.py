from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError

from app.core.config import Settings
from app.core.db import DbSession
from app.core.errors import UnauthorizedError
from app.core.security import decode_access_token
from app.models import User
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.earning_repository import EarningRepository
from app.repositories.fuel_price_repository import FuelPriceRepository
from app.repositories.fuel_repository import FuelRepository
from app.repositories.shift_repository import ShiftRepository
from app.repositories.track_point_repository import TrackPointRepository
from app.repositories.user_repository import UserRepository
from app.repositories.vehicle_repository import VehicleRepository
from app.services.analytics_service import AnalyticsService
from app.services.auth_service import AuthService
from app.services.calculations import CalculationParams
from app.services.earning_service import EarningService
from app.services.fuel_service import FuelService
from app.services.shift_service import ShiftService
from app.services.track_point_service import TrackPointService
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


def get_calculation_params(settings: AppSettings) -> CalculationParams:
    return CalculationParams(
        max_accuracy_m=settings.gps_max_accuracy_m,
        max_speed_kmh=settings.gps_max_speed_kmh,
        stationary_threshold_m=settings.gps_stationary_threshold_m,
        gap_threshold_s=settings.gps_gap_threshold_s,
        idle_fuel_ml_per_s=settings.idle_fuel_ml_per_s,
    )


def get_shift_service(
    db: DbSession, params: Annotated[CalculationParams, Depends(get_calculation_params)]
) -> ShiftService:
    return ShiftService(
        shifts=ShiftRepository(db),
        vehicles=VehicleRepository(db),
        prices=FuelPriceRepository(db),
        earnings=EarningRepository(db),
        track_points=TrackPointRepository(db),
        params=params,
    )


def get_earning_service(db: DbSession) -> EarningService:
    return EarningService(shifts=ShiftRepository(db), earnings=EarningRepository(db))


def get_track_point_service(db: DbSession) -> TrackPointService:
    return TrackPointService(shifts=ShiftRepository(db), track_points=TrackPointRepository(db))


def get_analytics_service(db: DbSession) -> AnalyticsService:
    return AnalyticsService(AnalyticsRepository(db))


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
ShiftServiceDep = Annotated[ShiftService, Depends(get_shift_service)]
EarningServiceDep = Annotated[EarningService, Depends(get_earning_service)]
TrackPointServiceDep = Annotated[TrackPointService, Depends(get_track_point_service)]
AnalyticsServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]
