import asyncio
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
from app.quick_router import router as quick_router
from app.surveys.router import router as surveys_router
from app.surveys import models as _surveys_models  # noqa: F401 — registra modelos
from app.surveys.seed import (
    seed_acta_inicio, seed_apuntes_reuniones, seed_diario_campo,
    seed_ficha_comision, seed_ficha_precampo,
    seed_registro_asistencia, seed_survey_catalog,
)
from app.audit.middleware import AuditMiddleware

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


async def _run_startup(retries: int = 5, delay: float = 3.0) -> None:
    """Ejecuta las migraciones de arranque con reintentos para tolerar el solapamiento de procesos uvicorn --reload."""
    for attempt in range(1, retries + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            # ALTER TYPE ADD VALUE no puede correr dentro de una transacción en PostgreSQL.
            async with engine.connect() as conn:
                await conn.execution_options(isolation_level="AUTOCOMMIT")
                for stmt in [
                    "ALTER TYPE corpus_tipo ADD VALUE IF NOT EXISTS 'otro'",
                    "ALTER TYPE corpus_estado ADD VALUE IF NOT EXISTS 'clasificado'",
                    "ALTER TABLE reports ADD COLUMN IF NOT EXISTS drive_file_id VARCHAR(200)",
                    "ALTER TABLE reports ADD COLUMN IF NOT EXISTS drive_url TEXT",
                    "ALTER TABLE study_corpus ADD COLUMN IF NOT EXISTS resumen TEXT",
                    "ALTER TABLE study_corpus ADD COLUMN IF NOT EXISTS texto_chars INTEGER",
                    "ALTER TABLE study_corpus ADD COLUMN IF NOT EXISTS fuente_extraccion VARCHAR(50)",
                    "ALTER TABLE study_corpus ADD COLUMN IF NOT EXISTS error_detalle TEXT",
                    "ALTER TABLE study_corpus ADD COLUMN IF NOT EXISTS clasificacion_fuente VARCHAR(40)",
                    "ALTER TABLE study_corpus ADD COLUMN IF NOT EXISTS clasificacion_confianza NUMERIC(4,3)",
                    "ALTER TABLE study_corpus ADD COLUMN IF NOT EXISTS notas_clasificacion TEXT",
                    # Sprint Drive B — JSON estructurado por archivo
                    "ALTER TABLE study_corpus ADD COLUMN IF NOT EXISTS datos_estructurados JSONB",
                    "ALTER TABLE study_corpus ADD COLUMN IF NOT EXISTS esquema_version VARCHAR(40)",
                    "ALTER TABLE study_corpus ADD COLUMN IF NOT EXISTS extraido_con_modelo VARCHAR(80)",
                    "ALTER TABLE study_corpus ADD COLUMN IF NOT EXISTS extraido_en_v2 TIMESTAMPTZ",
                    "ALTER TABLE study_corpus ADD COLUMN IF NOT EXISTS hash_sha256 VARCHAR(64)",
                    "CREATE INDEX IF NOT EXISTS ix_study_corpus_hash_sha256 ON study_corpus (hash_sha256)",
                    # Sprint Drive B — flag legacy en corpus_extractions
                    "ALTER TABLE corpus_extractions ADD COLUMN IF NOT EXISTS legacy BOOLEAN NOT NULL DEFAULT false",
                    "CREATE INDEX IF NOT EXISTS ix_corpus_extractions_legacy ON corpus_extractions (legacy)",
                    # Backfill: las extracciones existentes (del pipeline viejo) quedan marcadas legacy=true
                    "UPDATE corpus_extractions SET legacy = true WHERE legacy = false AND extraido_en < CURRENT_DATE",
                    "ALTER TABLE studies ADD COLUMN IF NOT EXISTS modo_creacion VARCHAR(30) DEFAULT 'drive_existente' NOT NULL",
                    # Sprint Drive E — overrides del consolidado
                    "ALTER TABLE studies ADD COLUMN IF NOT EXISTS consolidacion_overrides JSONB",
                ]:
                    await conn.execute(text(stmt))
            return
        except Exception as exc:
            if attempt == retries:
                raise
            logging.warning("Startup DB error (intento %d/%d): %s — reintentando en %.0fs…", attempt, retries, exc, delay)
            await asyncio.sleep(delay)


def _check_ai_provider() -> None:
    """Validar que el proveedor de IA esté operativo al arrancar."""
    if settings.AI_PROVIDER.lower() == "none" or not settings.AI_API_KEY:
        logging.warning("⚠ AI_PROVIDER no configurado — los PDFs escaneados no se procesarán")
        return
    try:
        from app.documents.ai_extractor import get_ai_extractor
        extractor = get_ai_extractor(
            provider=settings.AI_PROVIDER,
            api_key=settings.AI_API_KEY,
            model=settings.AI_MODEL,
        )
        if not extractor:
            logging.warning("⚠ No se pudo inicializar el extractor IA (provider=%s)", settings.AI_PROVIDER)
            return
        test = extractor.summarize("Documento de prueba.", "ping.txt")
        if test:
            logging.info("✓ IA operativa (provider=%s, model=%s)", settings.AI_PROVIDER, settings.AI_MODEL)
        else:
            logging.warning("⚠ IA respondió vacío al ping de arranque (provider=%s)", settings.AI_PROVIDER)
    except Exception as e:
        logging.error("⚠ IA no operativa al arrancar: %s — los archivos escaneados podrían fallar", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _run_startup()
    # Seed catálogo de encuestas (idempotente)
    from app.database import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as db:
            await seed_survey_catalog(db)
            await seed_ficha_precampo(db)
            await seed_acta_inicio(db)
            await seed_registro_asistencia(db)
            await seed_ficha_comision(db)
            await seed_diario_campo(db)
            await seed_apuntes_reuniones(db)
            await db.commit()
    except Exception as e:
        logging.warning("Seed encuestas falló: %s", e)
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
    allow_origin_regex=r"https://.*\.onrender\.com",
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
app.include_router(quick_router)
app.include_router(surveys_router)


@app.get("/health", tags=["sistema"])
async def health():
    return {"status": "ok", "version": "1.0.0"}
