"""Endpoints del módulo de encuestas."""
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.service import get_current_user
from app.database import get_db
from app.surveys import service
from app.surveys.models import SurveyResponse, SurveyType
from app.surveys.schemas import (
    AnswersBulkInput, JournalEntriesReplaceInput, PersonsReplaceInput,
    SurveyResponseDetail, SurveyResponseSummary,
    SurveyTypeFull, SurveyTypeSummary,
)

router = APIRouter(tags=["surveys"])


# ── Catálogo ──────────────────────────────────────────────────────────────────

@router.get("/api/surveys/types", response_model=list[SurveyTypeSummary])
async def list_survey_types(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listado del catálogo, ordenado por fase y orden."""
    result = await db.execute(
        select(SurveyType)
        .where(SurveyType.activo.is_(True))
        .order_by(SurveyType.fase, SurveyType.orden)
    )
    return result.scalars().all()


@router.get("/api/surveys/types/{code}", response_model=SurveyTypeFull)
async def get_survey_type(
    code: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Detalle completo: tipo + secciones + preguntas."""
    return await service.get_survey_type_full(db, code)


# ── Estado por estudio ────────────────────────────────────────────────────────

@router.get("/api/studies/{study_id}/surveys", response_model=list[SurveyResponseSummary])
async def list_study_surveys(
    study_id: UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista las 8 encuestas con el estado actual para el estudio dado."""
    types_result = await db.execute(
        select(SurveyType)
        .where(SurveyType.activo.is_(True))
        .order_by(SurveyType.fase, SurveyType.orden)
    )
    types = types_result.scalars().all()

    resps_result = await db.execute(
        select(SurveyResponse).where(SurveyResponse.study_id == study_id)
    )
    resps_by_type: dict[UUID, SurveyResponse] = {
        r.survey_type_id: r for r in resps_result.scalars().all()
    }

    out: list[SurveyResponseSummary] = []
    for t in types:
        r = resps_by_type.get(t.id)
        out.append(SurveyResponseSummary(
            survey_type_code=t.code,
            survey_type_nombre=t.nombre,
            fase=t.fase,
            orden=t.orden,
            estado=r.estado if r else "no_iniciada",
            response_id=r.id if r else None,
            updated_at=r.updated_at if r else None,
            completed_at=r.completed_at if r else None,
        ))
    return out


# ── CRUD de responses ─────────────────────────────────────────────────────────

@router.get("/api/studies/{study_id}/surveys/{code}", response_model=SurveyResponseDetail | None)
async def get_response(
    study_id: UUID,
    code: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Devuelve la response del estudio para ese tipo, o null si no se ha iniciado."""
    type_row = (await db.execute(select(SurveyType).where(SurveyType.code == code))).scalar_one_or_none()
    if not type_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de encuesta no encontrado")
    resp = (await db.execute(
        select(SurveyResponse).where(
            SurveyResponse.study_id == study_id,
            SurveyResponse.survey_type_id == type_row.id,
        )
    )).scalar_one_or_none()
    if not resp:
        return None
    return await service.build_response_detail(db, resp)


@router.post("/api/studies/{study_id}/surveys/{code}", response_model=SurveyResponseDetail, status_code=201)
async def start_response(
    study_id: UUID,
    code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crea la response si no existe (idempotente). Devuelve siempre el detalle completo."""
    resp = await service.get_or_create_response(db, study_id, code, current_user.id)
    return await service.build_response_detail(db, resp)


@router.put("/api/studies/{study_id}/surveys/{code}/answers", response_model=SurveyResponseDetail)
async def put_answers(
    study_id: UUID,
    code: str,
    payload: AnswersBulkInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upsert masivo de respuestas. Crea la response si no existe."""
    resp = await service.get_or_create_response(db, study_id, code, current_user.id)
    await service.upsert_answers(db, resp.id, payload.answers)
    return await service.build_response_detail(db, resp)


@router.put("/api/studies/{study_id}/surveys/{code}/persons", response_model=SurveyResponseDetail)
async def put_persons(
    study_id: UUID,
    code: str,
    payload: PersonsReplaceInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reemplaza la lista de personas de una pregunta tipo table_persons."""
    resp = await service.get_or_create_response(db, study_id, code, current_user.id)
    await service.replace_persons(db, resp.id, payload.question_code, payload.persons)
    return await service.build_response_detail(db, resp)


@router.put("/api/studies/{study_id}/surveys/{code}/journal", response_model=SurveyResponseDetail)
async def put_journal(
    study_id: UUID,
    code: str,
    payload: JournalEntriesReplaceInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reemplaza la lista de entradas de journal (diario / apuntes) para una pregunta."""
    resp = await service.get_or_create_response(db, study_id, code, current_user.id)
    await service.replace_journal_entries(db, resp.id, payload.question_code, payload.entries)
    return await service.build_response_detail(db, resp)


@router.post("/api/studies/{study_id}/surveys/{code}/complete", response_model=SurveyResponseDetail)
async def post_complete(
    study_id: UUID,
    code: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Completa la encuesta, genera PDF, lo enlaza al corpus y dispara procesamiento IA."""
    resp = await service.get_or_create_response(db, study_id, code, current_user.id)
    await service.complete_response(db, resp.id)
    # Generar PDF y enlazar al corpus
    await service.generate_pdf_for_response(db, resp.id)
    corpus_file = await service.link_response_to_corpus(db, resp.id)
    await db.commit()
    # Procesar con IA en background (no bloquear la respuesta)
    background_tasks.add_task(service.process_corpus_file_with_ai, corpus_file.id)
    return await service.build_response_detail(db, resp)


@router.get("/api/studies/{study_id}/surveys/{code}/pdf")
async def get_pdf(
    study_id: UUID,
    code: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Devuelve el PDF de una response. Si no existe aún, lo genera al vuelo (como borrador)."""
    type_row = (await db.execute(select(SurveyType).where(SurveyType.code == code))).scalar_one_or_none()
    if not type_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de encuesta no encontrado")
    resp = (await db.execute(
        select(SurveyResponse).where(
            SurveyResponse.study_id == study_id,
            SurveyResponse.survey_type_id == type_row.id,
        )
    )).scalar_one_or_none()
    if not resp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encuesta no iniciada")

    pdf_bytes, filename, _path = await service.generate_pdf_for_response(db, resp.id)
    await db.commit()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
