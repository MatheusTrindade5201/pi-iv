from fastapi import FastAPI

from app.routers import (
    auth,
    earnings,
    fuel_prices,
    fuels,
    health,
    shifts,
    users,
    vehicles,
)

ROUTERS = (
    health.router,
    auth.router,
    users.router,
    fuels.router,
    fuel_prices.router,
    vehicles.router,
    shifts.router,
    earnings.router,
)


def register_routers(app: FastAPI, prefix: str) -> None:
    for router in ROUTERS:
        app.include_router(router, prefix=prefix)
