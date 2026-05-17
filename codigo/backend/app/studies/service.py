from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status

from app.auth.models import User
from app.studies.models import Study, StudyCorpus, CorpusExtraction, GISResult, Report
from app.studies.schemas import StudyCreate, StudyUpdate, CorpusFileCreate

# Valid state machine transitions
_ALLOWED_TRANSITIONS: dict[str, list[str]] = {
    "borrador":        ["sincronizando"],
    "sincronizando":   ["corpus_ok", "error"],
    "corpus_ok":       ["procesando", "sincronizando"],
    "procesando":      ["listo_revision", "error"],
    "listo_revision":  ["en_revision", "procesando"],
    "en_revision":     ["aprobado", "listo_revision"],
    "aprobado":        ["exportado"],
    "exportado":       [],
    "error":           ["borrador", "sincronizando"],
}


# ── Study CRUD ────────────────────────────────────────────────────────────────

async def list_studies(
    db: AsyncSession,
    estado: str | None = None,
    departamento: str | None = None,
    responsable_id: UUID | None = None,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[Study], int]:
    query = select(Study)
    if estado:
        query = query.where(Study.estado == estado)
    if departamento:
        query = query.where(Study.departamento.ilike(f"%{departamento}%"))
    if responsable_id:
        query = query.where(Study.responsable_id == responsable_id)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    query = (
        query.offset((page - 1) * limit)
        .limit(limit)
        .order_by(Study.updated_at.desc())
    )
    result = await db.execute(query)
    return result.scalars().all(), total


async def get_study_or_404(db: AsyncSession, study_id: UUID) -> Study:
    result = await db.execute(select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    if not study:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estudio no encontrado")
    return study


async def create_study(db: AsyncSession, data: StudyCreate, created_by: UUID) -> Study:
    study = Study(
        **data.model_dump(exclude_none=True),
        created_by=created_by,
        estado="borrador",
    )
    db.add(study)
    await db.flush()
    await db.refresh(study)
    return study


async def update_study(db: AsyncSession, study_id: UUID, data: StudyUpdate) -> Study:
    study = await get_study_or_404(db, study_id)
    if study.estado not in ("borrador", "error"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se puede editar un estudio en estado '{study.estado}'",
        )
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(study, field, value)
    await db.flush()
    await db.refresh(study)
    return study


async def delete_study(db: AsyncSession, study_id: UUID) -> None:
    study = await get_study_or_404(db, study_id)
    if study.estado not in ("borrador", "error"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se pueden eliminar estudios en estado 'borrador' o 'error'",
        )
    await db.delete(study)
    await db.flush()


async def transition_state(
    db: AsyncSession, study_id: UUID, new_state: str, error_msg: str | None = None
) -> Study:
    study = await get_study_or_404(db, study_id)
    allowed = _ALLOWED_TRANSITIONS.get(study.estado, [])
    if new_state not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Transición inválida: '{study.estado}' → '{new_state}'. Permitidas: {allowed}",
        )
    study.estado = new_state
    study.error_msg = error_msg if new_state == "error" else None
    await db.flush()
    await db.refresh(study)
    return study


# ── Corpus ────────────────────────────────────────────────────────────────────

async def list_corpus(db: AsyncSession, study_id: UUID) -> list[StudyCorpus]:
    await get_study_or_404(db, study_id)
    result = await db.execute(
        select(StudyCorpus)
        .where(StudyCorpus.study_id == study_id)
        .order_by(StudyCorpus.fase, StudyCorpus.nombre_archivo)
    )
    return result.scalars().all()


async def add_corpus_file(
    db: AsyncSession, study_id: UUID, data: CorpusFileCreate
) -> StudyCorpus:
    await get_study_or_404(db, study_id)
    corpus_file = StudyCorpus(study_id=study_id, **data.model_dump(exclude_none=True))
    db.add(corpus_file)
    await db.flush()
    await db.refresh(corpus_file)
    return corpus_file


async def delete_corpus_file(db: AsyncSession, study_id: UUID, file_id: UUID) -> None:
    result = await db.execute(
        select(StudyCorpus).where(
            StudyCorpus.id == file_id, StudyCorpus.study_id == study_id
        )
    )
    corpus_file = result.scalar_one_or_none()
    if not corpus_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archivo no encontrado")
    await db.delete(corpus_file)
    await db.flush()


# ── Extractions ───────────────────────────────────────────────────────────────

async def list_extractions(db: AsyncSession, study_id: UUID) -> list[CorpusExtraction]:
    await get_study_or_404(db, study_id)
    result = await db.execute(
        select(CorpusExtraction)
        .where(CorpusExtraction.study_id == study_id)
        .order_by(CorpusExtraction.tipo_dato)
    )
    return result.scalars().all()


# ── GIS Results ───────────────────────────────────────────────────────────────

async def list_gis_results(db: AsyncSession, study_id: UUID) -> list[GISResult]:
    await get_study_or_404(db, study_id)
    result = await db.execute(
        select(GISResult)
        .where(GISResult.study_id == study_id)
        .order_by(GISResult.generado_en.desc())
    )
    return result.scalars().all()


# ── Reports ───────────────────────────────────────────────────────────────────

async def list_reports(db: AsyncSession, study_id: UUID) -> list[Report]:
    await get_study_or_404(db, study_id)
    result = await db.execute(
        select(Report)
        .where(Report.study_id == study_id)
        .order_by(Report.version.desc())
    )
    return result.scalars().all()
