from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.service import get_current_user, require_tecnico
from app.auth.models import User
from app.documents import service

router = APIRouter(prefix="/api/studies/{study_id}/documents", tags=["documents"])


@router.post("/process", status_code=202)
async def process_corpus(
    study_id: UUID,
    reprocess: bool = Query(False, description="Si True, elimina extracciones previas y reprocesa"),
    _: User = Depends(require_tecnico),
    db: AsyncSession = Depends(get_db),
):
    """
    Procesa los archivos PDF/DOCX del corpus con NLP (spaCy).
    Extrae entidades, nombres, fechas, cifras de población y las guarda en BD.
    El corpus debe estar sincronizado desde Drive primero.
    """
    result = await service.process_study_corpus(db, study_id, reprocess=reprocess)
    await db.commit()
    return result


@router.get("/extractions/summary")
async def extraction_summary(
    study_id: UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resumen de entidades extraídas agrupadas por tipo."""
    return await service.get_extraction_summary(db, study_id)
