from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.service import get_current_user, require_tecnico, require_supervisor
from app.auth.models import User
from app.studies import schemas, service

router = APIRouter(prefix="/api/studies", tags=["studies"])


# ── Studies ───────────────────────────────────────────────────────────────────

@router.get("", response_model=schemas.StudyListResponse)
async def list_studies(
    estado: str | None = Query(None),
    departamento: str | None = Query(None),
    responsable_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    studies, total = await service.list_studies(
        db, estado=estado, departamento=departamento,
        responsable_id=responsable_id, page=page, limit=limit,
    )
    return schemas.StudyListResponse(
        total=total, page=page, limit=limit,
        items=[schemas.StudySummary.model_validate(s) for s in studies],
    )


@router.post("", response_model=schemas.StudyResponse, status_code=201)
async def create_study(
    data: schemas.StudyCreate,
    current_user: User = Depends(require_tecnico),
    db: AsyncSession = Depends(get_db),
):
    study = await service.create_study(db, data, created_by=current_user.id)
    return schemas.StudyResponse.model_validate(study)


@router.get("/{study_id}", response_model=schemas.StudyResponse)
async def get_study(
    study_id: UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    study = await service.get_study_or_404(db, study_id)
    return schemas.StudyResponse.model_validate(study)


@router.put("/{study_id}", response_model=schemas.StudyResponse)
async def update_study(
    study_id: UUID,
    data: schemas.StudyUpdate,
    _: User = Depends(require_tecnico),
    db: AsyncSession = Depends(get_db),
):
    study = await service.update_study(db, study_id, data)
    return schemas.StudyResponse.model_validate(study)


@router.delete("/{study_id}", status_code=204)
async def delete_study(
    study_id: UUID,
    _: User = Depends(require_tecnico),
    db: AsyncSession = Depends(get_db),
):
    await service.delete_study(db, study_id)
    return None


@router.post("/{study_id}/transition", response_model=schemas.StudyResponse)
async def transition_state(
    study_id: UUID,
    data: schemas.StudyStateTransition,
    _: User = Depends(require_supervisor),
    db: AsyncSession = Depends(get_db),
):
    study = await service.transition_state(db, study_id, data.estado, data.error_msg)
    return schemas.StudyResponse.model_validate(study)


# ── Corpus ────────────────────────────────────────────────────────────────────

@router.get("/{study_id}/corpus", response_model=list[schemas.CorpusFileResponse])
async def list_corpus(
    study_id: UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    files = await service.list_corpus(db, study_id)
    return [schemas.CorpusFileResponse.model_validate(f) for f in files]


@router.post("/{study_id}/corpus", response_model=schemas.CorpusFileResponse, status_code=201)
async def add_corpus_file(
    study_id: UUID,
    data: schemas.CorpusFileCreate,
    _: User = Depends(require_tecnico),
    db: AsyncSession = Depends(get_db),
):
    corpus_file = await service.add_corpus_file(db, study_id, data)
    return schemas.CorpusFileResponse.model_validate(corpus_file)


@router.delete("/{study_id}/corpus/{file_id}", status_code=204)
async def delete_corpus_file(
    study_id: UUID,
    file_id: UUID,
    _: User = Depends(require_tecnico),
    db: AsyncSession = Depends(get_db),
):
    await service.delete_corpus_file(db, study_id, file_id)
    return None


# ── Extractions ───────────────────────────────────────────────────────────────

@router.get("/{study_id}/extractions", response_model=list[schemas.ExtractionResponse])
async def list_extractions(
    study_id: UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    extractions = await service.list_extractions(db, study_id)
    return [schemas.ExtractionResponse.model_validate(e) for e in extractions]


# ── GIS Results ───────────────────────────────────────────────────────────────

@router.get("/{study_id}/gis", response_model=list[schemas.GISResultResponse])
async def list_gis_results(
    study_id: UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    results = await service.list_gis_results(db, study_id)
    return [schemas.GISResultResponse.model_validate(r) for r in results]


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/{study_id}/reports", response_model=list[schemas.ReportResponse])
async def list_reports(
    study_id: UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    reports = await service.list_reports(db, study_id)
    return [schemas.ReportResponse.model_validate(r) for r in reports]
