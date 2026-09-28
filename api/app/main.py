from fastapi import FastAPI

from app.core.config import Settings, get_settings
from app.routers import health


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.include_router(health.router, prefix=settings.api_prefix)

    return app


app = create_app()
