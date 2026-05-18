import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

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
    # Crear tablas que no existan
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # ALTER TYPE ADD VALUE no puede correr dentro de una transacción en PostgreSQL;
    # necesita AUTOCOMMIT. Se ejecuta en una conexión separada.
    async with engine.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        await conn.execute(text(
            "ALTER TYPE corpus_tipo ADD VALUE IF NOT EXISTS 'otro'"
        ))
        # Columnas añadidas post-creación inicial de la tabla reports
        await conn.execute(text(
            "ALTER TABLE reports ADD COLUMN IF NOT EXISTS drive_file_id VARCHAR(200)"
        ))
        await conn.execute(text(
            "ALTER TABLE reports ADD COLUMN IF NOT EXISTS drive_url TEXT"
        ))

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
    allow_origins=settings.allowed_origins_list,
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
