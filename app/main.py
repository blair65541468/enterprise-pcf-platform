from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import models  # noqa: F401
from app.api import admin, calculations, health, imports, products
from app.config import settings
from app.db import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(engine)
    yield


app = FastAPI(
    title="Enterprise PCF Platform",
    version=settings.app_version,
    description="Auditable PCF middleware for openLCA REST",
    lifespan=lifespan,
)
app.include_router(health.router)
app.include_router(imports.router)
app.include_router(products.router)
app.include_router(calculations.router)
app.include_router(admin.router)

