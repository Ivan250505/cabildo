from uuid import UUID
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.service import get_current_user, require_tecnico, require_supervisor
from app.auth.models import User
from app.reports import service
from app.studies.schemas import ReportResponse

router = APIRouter(prefix="/api/studies/{study_id}/reports", tags=["reports"])


@router.post("", response_model=ReportResponse, status_code=201)
async def generate_report(
    study_id: UUID,
    current_user: User = Depends(require_tecnico),
    db: AsyncSession = Depends(get_db),
):
    """
    Genera el informe Word del estudio.
    El estudio debe estar en estado 'corpus_ok', 'listo_revision' o 'en_revision'.
    """
    report = await service.generate_report(
        db, study_id, generado_por=current_user.id
    )
    await db.commit()
    return ReportResponse.model_validate(report)


@router.post("/{report_id}/approve", response_model=ReportResponse)
async def approve_report(
    study_id: UUID,
    report_id: UUID,
    current_user: User = Depends(require_supervisor),
    db: AsyncSession = Depends(get_db),
):
    """Aprueba el informe. Solo supervisores y admins."""
    report = await service.approve_report(db, study_id, report_id, current_user.id)
    await db.commit()
    return ReportResponse.model_validate(report)


@router.get("/{report_id}/download")
async def download_report(
    study_id: UUID,
    report_id: UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Descarga el archivo .docx del informe."""
    docx_bytes, filename = await service.get_report_bytes(db, study_id, report_id)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
