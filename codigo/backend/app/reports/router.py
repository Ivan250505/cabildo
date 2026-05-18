from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.service import get_current_user, require_tecnico, require_supervisor
from app.auth.models import User
from app.reports import service
from app.studies.schemas import ReportResponse

router = APIRouter(prefix="/api/studies/{study_id}/reports", tags=["reports"])


@router.get("", response_model=list[ReportResponse])
async def list_reports(
    study_id: UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos los informes de un estudio, ordenados por versión descendente."""
    reports = await service.list_reports(db, study_id)
    return [ReportResponse.model_validate(r) for r in reports]


@router.post("", response_model=ReportResponse, status_code=202)
async def generate_report(
    study_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_tecnico),
    db: AsyncSession = Depends(get_db),
):
    """
    Inicia la generación del informe Word en segundo plano.
    Devuelve 202 con el Report en estado 'generando'. Seguir el progreso via GET /reports.
    """
    report = await service.start_report(db, study_id, generado_por=current_user.id)
    await db.commit()
    background_tasks.add_task(service.build_report_bg, study_id, report.id)
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
