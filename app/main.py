from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app import models  # noqa: F401
from app.api import admin, calculations, health, imports, products
from app.config import settings
from app.core.exceptions import DomainError
from app.core.immutability import register_immutability_guards
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.db import Base, engine

configure_logging()
register_immutability_guards()


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
app.add_middleware(RequestContextMiddleware)


@app.exception_handler(DomainError)
async def handle_domain_error(_request, exc: DomainError):
    detail = exc.message if not exc.details else {"code": exc.code, "message": exc.message, **exc.details}
    return JSONResponse(status_code=exc.status_code, content={"detail": detail})


app.include_router(health.router)
app.include_router(imports.router)
app.include_router(products.router)
app.include_router(calculations.router)
app.include_router(admin.router)
