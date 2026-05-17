import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import engine, Base
from app.auth.router import router as auth_router
from app.users.router import router as users_router
from app.studies.router import router as studies_router
from app.drive.router import router as drive_router
from app.reports.router import router as reports_router
from app.gis.router import router as gis_router
from app.map.router import router as map_router
from app.documents.router import router as documents_router
from app.audit.middleware import AuditMiddleware

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # En desarrollo crea las tablas automáticamente.
    # En producción se usa Alembic: `alembic upgrade head`
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="EtnIA API",
    description="Plataforma de automatización de estudios etnológicos — Simonky S.A.S.",
    version="1.0.0",
    lifespan=lifespan,
)

# Middleware (orden importa: CORSMiddleware primero, luego AuditMiddleware)
app.add_middleware(AuditMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(studies_router)
app.include_router(drive_router)
app.include_router(documents_router)
app.include_router(gis_router)
app.include_router(reports_router)
app.include_router(map_router)


@app.get("/health", tags=["sistema"])
async def health():
    return {"status": "ok", "version": "1.0.0"}
