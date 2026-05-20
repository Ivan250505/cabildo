"""Service layer del módulo de encuestas."""
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.studies.models import CorpusExtraction, Study, StudyCorpus
from app.surveys.models import (
    SurveyAnswer, SurveyEvidence, SurveyJournalEntry, SurveyPerson, SurveyQuestion,
    SurveyResponse, SurveySection, SurveyType,
)
from app.surveys.pdf_generator import generate_survey_pdf
from app.surveys.schemas import (
    AnswerInput, JournalEntryInput, PersonInput, SurveyAnswerOut, SurveyEvidenceOut,
    SurveyJournalEntryOut, SurveyPersonOut, SurveyResponseDetail, SurveyTypeFull,
)

logger = logging.getLogger(__name__)
_settings = get_settings()


async def get_survey_type_full(db: AsyncSession, code: str) -> SurveyTypeFull:
    """Devuelve el tipo de encuesta con todas sus secciones y preguntas anidadas."""
    result = await db.execute(
        select(SurveyType)
        .where(SurveyType.code == code)
        .options(selectinload(SurveyType.sections).selectinload(SurveySection.questions))
    )
    survey_type = result.scalar_one_or_none()
    if not survey_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de encuesta no encontrado")
    return SurveyTypeFull.model_validate(survey_type)


async def _get_response(db: AsyncSession, study_id: UUID, survey_type_id: UUID) -> SurveyResponse | None:
    result = await db.execute(
        select(SurveyResponse).where(
            SurveyResponse.study_id == study_id,
            SurveyResponse.survey_type_id == survey_type_id,
        )
    )
    return result.scalar_one_or_none()


async def get_or_create_response(
    db: AsyncSession, study_id: UUID, type_code: str, user_id: UUID | None,
) -> SurveyResponse:
    """Devuelve la response del estudio para ese tipo, creándola si no existe."""
    type_row = (await db.execute(select(SurveyType).where(SurveyType.code == type_code))).scalar_one_or_none()
    if not type_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de encuesta no encontrado")

    existing = await _get_response(db, study_id, type_row.id)
    if existing:
        return existing

    response = SurveyResponse(
        study_id=study_id,
        survey_type_id=type_row.id,
        estado="borrador",
        version=type_row.version,
        created_by=user_id,
    )
    db.add(response)
    await db.flush()
    return response


async def build_response_detail(db: AsyncSession, response: SurveyResponse) -> SurveyResponseDetail:
    """Construye el detalle completo de una response: type info + answers + persons + evidences."""
    # Type info
    type_row = (await db.execute(select(SurveyType).where(SurveyType.id == response.survey_type_id))).scalar_one()

    # Answers — necesitamos el question.code para que el frontend mapee
    answers_q = await db.execute(
        select(SurveyAnswer, SurveyQuestion)
        .join(SurveyQuestion, SurveyAnswer.question_id == SurveyQuestion.id)
        .where(SurveyAnswer.response_id == response.id)
    )
    answers_out = []
    for ans, q in answers_q.all():
        answers_out.append(SurveyAnswerOut(
            question_code=q.code,
            question_id=q.id,
            valor_texto=ans.valor_texto,
            valor_numero=float(ans.valor_numero) if ans.valor_numero is not None else None,
            valor_fecha=ans.valor_fecha,
            valor_bool=ans.valor_bool,
            valor_json=ans.valor_json,
        ))

    # Persons
    persons_q = await db.execute(
        select(SurveyPerson, SurveyQuestion)
        .join(SurveyQuestion, SurveyPerson.question_id == SurveyQuestion.id)
        .where(SurveyPerson.response_id == response.id)
        .order_by(SurveyPerson.orden)
    )
    persons_out = []
    for p, q in persons_q.all():
        persons_out.append(SurveyPersonOut(
            id=p.id, question_code=q.code, orden=p.orden,
            nombre=p.nombre, documento=p.documento, genero=p.genero,
            edad=p.edad, cargo=p.cargo, ocupacion=p.ocupacion,
            escolaridad=p.escolaridad, contacto=p.contacto, pueblo=p.pueblo,
            extra=p.extra,
        ))

    # Evidences
    ev_q = await db.execute(
        select(SurveyEvidence, SurveyQuestion)
        .join(SurveyQuestion, SurveyEvidence.question_id == SurveyQuestion.id)
        .where(SurveyEvidence.response_id == response.id)
        .order_by(SurveyEvidence.orden)
    )
    evidences_out = []
    for e, q in ev_q.all():
        evidences_out.append(SurveyEvidenceOut(
            id=e.id, question_code=q.code, categoria=e.categoria,
            orden=e.orden, titulo=e.titulo, descripcion=e.descripcion,
        ))

    # Journal entries
    jr_q = await db.execute(
        select(SurveyJournalEntry, SurveyQuestion)
        .join(SurveyQuestion, SurveyJournalEntry.question_id == SurveyQuestion.id)
        .where(SurveyJournalEntry.response_id == response.id)
        .order_by(SurveyJournalEntry.orden)
    )
    journal_out = []
    for j, q in jr_q.all():
        journal_out.append(SurveyJournalEntryOut(
            id=j.id, question_code=q.code, orden=j.orden,
            fecha=j.fecha, titulo=j.titulo, contenido=j.contenido,
            tags=j.tags, extra=j.extra,
        ))

    return SurveyResponseDetail(
        id=response.id,
        study_id=response.study_id,
        survey_type_code=type_row.code,
        survey_type_nombre=type_row.nombre,
        fase=type_row.fase,
        estado=response.estado,
        version=response.version,
        created_at=response.created_at,
        updated_at=response.updated_at,
        completed_at=response.completed_at,
        pdf_url=response.pdf_url,
        answers=answers_out,
        persons=persons_out,
        evidences=evidences_out,
        journal_entries=journal_out,
    )


async def upsert_answers(db: AsyncSession, response_id: UUID, items: list[AnswerInput]) -> None:
    """Upsert masivo de respuestas. Identifica preguntas por question_code dentro del survey_type."""
    if not items:
        return

    # Cargar la response y su survey_type para resolver question codes → ids
    resp = (await db.execute(select(SurveyResponse).where(SurveyResponse.id == response_id))).scalar_one_or_none()
    if not resp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response no encontrada")

    # Map question_code → question_id (solo preguntas del survey_type de esta response)
    questions = await db.execute(
        select(SurveyQuestion.id, SurveyQuestion.code)
        .join(SurveySection, SurveyQuestion.section_id == SurveySection.id)
        .where(SurveySection.survey_type_id == resp.survey_type_id)
    )
    code_to_id: dict[str, UUID] = {code: qid for qid, code in questions.all()}

    # Existing answers para upsert
    existing_q = await db.execute(
        select(SurveyAnswer).where(SurveyAnswer.response_id == response_id)
    )
    existing_by_qid: dict[UUID, SurveyAnswer] = {a.question_id: a for a in existing_q.scalars().all()}

    for item in items:
        qid = code_to_id.get(item.question_code)
        if not qid:
            # Pregunta no existe en este survey_type — ignorar silenciosamente
            continue
        ans = existing_by_qid.get(qid)
        if ans:
            ans.valor_texto = item.valor_texto
            ans.valor_numero = item.valor_numero
            ans.valor_fecha = item.valor_fecha
            ans.valor_bool = item.valor_bool
            ans.valor_json = item.valor_json
        else:
            db.add(SurveyAnswer(
                response_id=response_id,
                question_id=qid,
                valor_texto=item.valor_texto,
                valor_numero=item.valor_numero,
                valor_fecha=item.valor_fecha,
                valor_bool=item.valor_bool,
                valor_json=item.valor_json,
            ))

    resp.updated_at = datetime.now(timezone.utc)
    await db.flush()


async def replace_persons(
    db: AsyncSession, response_id: UUID, question_code: str, items: list[PersonInput],
) -> None:
    """Reemplaza todas las personas asociadas a una pregunta dentro de una response."""
    resp = (await db.execute(select(SurveyResponse).where(SurveyResponse.id == response_id))).scalar_one_or_none()
    if not resp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response no encontrada")

    # Resolver question_id
    q_row = await db.execute(
        select(SurveyQuestion)
        .join(SurveySection, SurveyQuestion.section_id == SurveySection.id)
        .where(
            SurveySection.survey_type_id == resp.survey_type_id,
            SurveyQuestion.code == question_code,
        )
    )
    question = q_row.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pregunta no encontrada en esta encuesta")

    # Borrar existentes
    await db.execute(
        delete(SurveyPerson).where(
            SurveyPerson.response_id == response_id,
            SurveyPerson.question_id == question.id,
        )
    )
    # Insertar nuevos
    for idx, item in enumerate(items):
        db.add(SurveyPerson(
            response_id=response_id,
            question_id=question.id,
            orden=item.orden if item.orden else idx,
            nombre=item.nombre,
            documento=item.documento,
            genero=item.genero,
            edad=item.edad,
            cargo=item.cargo,
            ocupacion=item.ocupacion,
            escolaridad=item.escolaridad,
            contacto=item.contacto,
            pueblo=item.pueblo,
            extra=item.extra,
        ))

    resp.updated_at = datetime.now(timezone.utc)
    await db.flush()


async def replace_journal_entries(
    db: AsyncSession, response_id: UUID, question_code: str, items: list[JournalEntryInput],
) -> None:
    """Reemplaza todas las entradas de journal asociadas a una pregunta dentro de una response."""
    resp = (await db.execute(select(SurveyResponse).where(SurveyResponse.id == response_id))).scalar_one_or_none()
    if not resp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response no encontrada")

    q_row = await db.execute(
        select(SurveyQuestion)
        .join(SurveySection, SurveyQuestion.section_id == SurveySection.id)
        .where(
            SurveySection.survey_type_id == resp.survey_type_id,
            SurveyQuestion.code == question_code,
        )
    )
    question = q_row.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pregunta no encontrada en esta encuesta")

    await db.execute(
        delete(SurveyJournalEntry).where(
            SurveyJournalEntry.response_id == response_id,
            SurveyJournalEntry.question_id == question.id,
        )
    )
    for idx, item in enumerate(items):
        db.add(SurveyJournalEntry(
            response_id=response_id,
            question_id=question.id,
            orden=item.orden if item.orden else idx,
            fecha=item.fecha,
            titulo=item.titulo,
            contenido=item.contenido,
            tags=item.tags,
            extra=item.extra,
        ))

    resp.updated_at = datetime.now(timezone.utc)
    await db.flush()


async def complete_response(db: AsyncSession, response_id: UUID) -> SurveyResponse:
    """Marca una response como completada."""
    resp = (await db.execute(select(SurveyResponse).where(SurveyResponse.id == response_id))).scalar_one_or_none()
    if not resp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response no encontrada")
    resp.estado = "completada"
    resp.completed_at = datetime.now(timezone.utc)
    resp.updated_at = resp.completed_at
    await db.flush()
    return resp


# ── Generación de PDF + integración con corpus ─────────────────────────────────

async def generate_pdf_for_response(
    db: AsyncSession, response_id: UUID,
) -> tuple[bytes, str, Path]:
    """Genera el PDF, lo guarda en disco y devuelve (bytes, filename, ruta_absoluta)."""
    resp = (await db.execute(select(SurveyResponse).where(SurveyResponse.id == response_id))).scalar_one_or_none()
    if not resp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response no encontrada")

    pdf_bytes, filename = await generate_survey_pdf(db, response_id)

    # Guardar en disco: storage/files/{study_id}/surveys/{response_id}.pdf
    out_dir = Path(_settings.FILES_BASE_PATH) / str(resp.study_id) / "surveys"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{response_id}.pdf"
    out_path.write_bytes(pdf_bytes)

    resp.pdf_url = str(out_path)
    await db.flush()
    return pdf_bytes, filename, out_path


def _fase_from_survey_fase(fase: str) -> str:
    """survey_type.fase ('FASE1'/'FASE2') ya coincide con study_corpus.fase."""
    return fase


async def link_response_to_corpus(db: AsyncSession, response_id: UUID) -> StudyCorpus:
    """Crea/actualiza la fila en study_corpus correspondiente al PDF de la encuesta.

    Reutiliza la fila si ya existe (por survey_response.corpus_file_id) para no duplicar
    cuando el usuario completa la encuesta más de una vez.
    """
    resp = (await db.execute(
        select(SurveyResponse).where(SurveyResponse.id == response_id)
    )).scalar_one_or_none()
    if not resp or not resp.pdf_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La response no tiene PDF generado")

    survey_type = (await db.execute(
        select(SurveyType).where(SurveyType.id == resp.survey_type_id)
    )).scalar_one()
    study = (await db.execute(select(Study).where(Study.id == resp.study_id))).scalar_one()

    nombre_archivo = f"{survey_type.code}_{study.nombre_comunidad.replace(' ', '_')}.pdf"
    drive_id_sentinel = f"formulario-{response_id}"
    fase = _fase_from_survey_fase(survey_type.fase)
    now = datetime.now(timezone.utc)
    pdf_path = Path(resp.pdf_url)
    size = pdf_path.stat().st_size if pdf_path.exists() else None

    # Buscar existente
    existing = None
    if resp.corpus_file_id:
        existing = (await db.execute(
            select(StudyCorpus).where(StudyCorpus.id == resp.corpus_file_id)
        )).scalar_one_or_none()

    if existing:
        existing.nombre_archivo = nombre_archivo
        existing.fase = fase
        existing.tipo_archivo = "pdf"
        existing.rol_en_corpus = survey_type.code if survey_type.code in _CORPUS_ROLE_WHITELIST else "otro"
        existing.ruta_local = str(pdf_path)
        existing.tamanio_bytes = size
        existing.estado = "pendiente"
        existing.fuente_extraccion = "formulario"
        existing.error_msg = None
        existing.error_detalle = None
        existing.sync_at = now
        corpus_file = existing
    else:
        # Borrar extracciones previas si las hay (por reuso de nombre_archivo)
        await db.execute(
            delete(CorpusExtraction).where(
                CorpusExtraction.study_id == resp.study_id,
                CorpusExtraction.fuente_archivo == nombre_archivo,
            )
        )
        corpus_file = StudyCorpus(
            study_id=resp.study_id,
            fase=fase,
            nombre_archivo=nombre_archivo,
            drive_file_id=drive_id_sentinel,
            tipo_archivo="pdf",
            rol_en_corpus=survey_type.code if survey_type.code in _CORPUS_ROLE_WHITELIST else "otro",
            tamanio_bytes=size,
            ruta_local=str(pdf_path),
            estado="pendiente",
            fuente_extraccion="formulario",
            sync_at=now,
        )
        db.add(corpus_file)
        await db.flush()
        resp.corpus_file_id = corpus_file.id

    await db.flush()
    return corpus_file


# Rol válido en study_corpus.rol_en_corpus (CORPUS_ROLES en studies/models.py)
_CORPUS_ROLE_WHITELIST = {
    "solicitud_formal", "reglamento", "acta_eleccion", "acta_posesion",
    "autocenso_depurado", "autocenso", "censo_comunidad", "ficha_precampo",
    "rut_comunidad", "resena_historica", "mapa_territorial", "base_datos_dane",
    "acta_inicio", "cronograma", "diario_campo", "ficha_comision",
    "apuntes_reuniones", "arbol_riesgo", "cartografia_social", "registro_asistencia",
    "proyecto_qgis", "geopackage", "evidencia_foto",
    "concepto_etnologico", "borrador_acto_administrativo", "otro",
}


async def process_corpus_file_with_ai(corpus_file_id: UUID) -> None:
    """Background task: extrae texto del PDF, lo pasa por IA (resumen + entidades).

    Abre su propia sesión de BD porque corre fuera del request.
    """
    from app.database import AsyncSessionLocal
    from app.documents.ai_extractor import _SKIP_SUMMARY_THRESHOLD, get_ai_extractor
    from app.documents.extractor import extract_text_pdf

    async with AsyncSessionLocal() as db:
        try:
            corpus_file = (await db.execute(
                select(StudyCorpus).where(StudyCorpus.id == corpus_file_id)
            )).scalar_one_or_none()
            if not corpus_file or not corpus_file.ruta_local:
                logger.warning("process_corpus_file_with_ai: corpus_file %s sin ruta_local", corpus_file_id)
                return

            pdf_path = Path(corpus_file.ruta_local)
            if not pdf_path.exists():
                corpus_file.estado = "error"
                corpus_file.error_msg = "Archivo PDF no encontrado en disco"
                await db.commit()
                return

            corpus_file.estado = "procesando" if False else corpus_file.estado  # noqa — el corpus_estado no incluye 'procesando'
            await db.commit()

            # Extracción de texto
            try:
                texto = extract_text_pdf(pdf_path)
            except Exception as e:
                logger.warning("Error extrayendo texto PDF %s: %s", pdf_path.name, e)
                texto = ""

            corpus_file.texto_chars = len(texto)

            extractor = get_ai_extractor(
                provider=_settings.AI_PROVIDER,
                api_key=_settings.AI_API_KEY,
                model=_settings.AI_MODEL,
            )

            # Resumen IA
            if extractor and texto and len(texto) <= _SKIP_SUMMARY_THRESHOLD:
                try:
                    resumen = extractor.summarize(texto, corpus_file.nombre_archivo, rol=corpus_file.rol_en_corpus)
                    if resumen:
                        corpus_file.resumen = resumen[:2000]
                except Exception as e:
                    logger.warning("Resumen IA del formulario falló: %s", e)

            # Extracción estructurada IA
            if extractor and texto:
                try:
                    entidades = extractor.extract(texto, corpus_file.nombre_archivo)
                    now = datetime.now(timezone.utc)
                    for ent in entidades:
                        valor = (ent.get("valor") or "").strip()
                        if not valor or len(valor) < 2:
                            continue
                        db.add(CorpusExtraction(
                            study_id=corpus_file.study_id,
                            tipo_dato=str(ent.get("tipo_dato", "otro"))[:100],
                            valor=valor[:500],
                            fuente_archivo=corpus_file.nombre_archivo,
                            confianza=float(ent.get("confianza", 0.9)),
                            extraido_en=now,
                        ))
                except Exception as e:
                    logger.warning("Extracción IA del formulario falló: %s", e)

            corpus_file.estado = "procesado"
            corpus_file.procesado_en = datetime.now(timezone.utc)
            await db.commit()
            logger.info("Encuesta procesada IA: %s", corpus_file.nombre_archivo)
        except Exception as e:
            logger.exception("Error procesando encuesta IA: %s", e)
            await db.rollback()
