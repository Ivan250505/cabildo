from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, AsyncSessionLocal
from app.auth.service import get_current_user, require_tecnico
from app.auth.models import User
from app.documents import service
from app.studies.models import Study

router = APIRouter(prefix="/api/studies/{study_id}/documents", tags=["documents"])


# Estado en memoria del último run del pipeline v2 por estudio. No persiste
# entre reinicios — solo sirve para que la UI sondee el progreso.
_v2_status: dict[str, dict] = {}


async def _bg_process(study_id: UUID, reprocess: bool) -> None:
    async with AsyncSessionLocal() as db:
        try:
            await service.process_study_corpus(db, study_id, reprocess)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            async with AsyncSessionLocal() as db2:
                result = await db2.execute(select(Study).where(Study.id == study_id))
                study = result.scalar_one_or_none()
                if study:
                    study.estado = "error"
                    study.error_msg = str(exc)[:500]
                    await db2.commit()


async def _bg_process_v2(study_id: UUID, reprocess: bool) -> None:
    from app.documents.pipeline_v2 import process_study_corpus_v2
    sid = str(study_id)
    _v2_status[sid] = {"estado": "corriendo", "summary": None, "error": None}
    async with AsyncSessionLocal() as db:
        try:
            summary = await process_study_corpus_v2(db, study_id, reprocess)
            await db.commit()
            _v2_status[sid] = {"estado": "ok", "summary": summary, "error": None}
        except Exception as exc:
            await db.rollback()
            _v2_status[sid] = {"estado": "error", "summary": None, "error": str(exc)[:500]}
            async with AsyncSessionLocal() as db2:
                result = await db2.execute(select(Study).where(Study.id == study_id))
                study = result.scalar_one_or_none()
                if study:
                    study.estado = "error"
                    study.error_msg = str(exc)[:500]
                    await db2.commit()


@router.post("/process", status_code=202)
async def process_corpus(
    study_id: UUID,
    background_tasks: BackgroundTasks,
    reprocess: bool = Query(False),
    _: User = Depends(require_tecnico),
    db: AsyncSession = Depends(get_db),
):
    """
    Inicia la extracción documental en segundo plano.
    Devuelve 202 inmediatamente. Seguir el progreso via GET /studies/{id} (campo estado).
    """
    result = await db.execute(select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    if not study:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Estudio no encontrado")

    study.estado = "procesando"
    await db.commit()

    background_tasks.add_task(_bg_process, study_id, reprocess)
    return {"status": "procesando", "study_id": str(study_id)}


@router.get("/extractions/summary")
async def extraction_summary(
    study_id: UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resumen de entidades extraídas agrupadas por tipo."""
    return await service.get_extraction_summary(db, study_id)


# ── Pipeline v2 (Sprint Drive C) ─────────────────────────────────────────────

@router.post("/process-v2", status_code=202)
async def process_corpus_v2(
    study_id: UUID,
    background_tasks: BackgroundTasks,
    reprocess: bool = Query(False),
    _: User = Depends(require_tecnico),
    db: AsyncSession = Depends(get_db),
):
    """
    Inicia el pipeline v2 en segundo plano:
      clasificar → extraer texto → extracción dirigida por rol → datos JSON.

    Devuelve 202 inmediatamente. Estado en GET /process-v2/status.
    """
    result = await db.execute(select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    if not study:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Estudio no encontrado")

    study.estado = "procesando"
    await db.commit()

    background_tasks.add_task(_bg_process_v2, study_id, reprocess)
    return {"status": "procesando", "study_id": str(study_id), "pipeline": "v2"}


@router.get("/process-v2/status")
async def process_corpus_v2_status(
    study_id: UUID,
    _: User = Depends(get_current_user),
):
    """Devuelve el último estado del run v2 en memoria."""
    return _v2_status.get(str(study_id)) or {"estado": "sin_runs", "summary": None, "error": None}
