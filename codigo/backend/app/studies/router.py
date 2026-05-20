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


# ── Clasificación de archivos (Sprint Drive A) ────────────────────────────────

@router.post(
    "/{study_id}/corpus/clasificar",
    response_model=schemas.CorpusClasificarResponse,
)
async def clasificar_corpus(
    study_id: UUID,
    data: schemas.CorpusClasificarRequest | None = None,
    _: User = Depends(require_tecnico),
    db: AsyncSession = Depends(get_db),
):
    """
    Clasifica todos los archivos del corpus del estudio aplicando la cascada
    heurística (extensión / carpeta / nombre) y, si está habilitado, IA corta
    sobre las primeras páginas. Los archivos marcados como 'manual' nunca se
    sobrescriben.
    """
    from app.documents.classify_service import classify_study_corpus

    params = data or schemas.CorpusClasificarRequest()
    result = await classify_study_corpus(
        db, study_id,
        ignore_existing=params.ignore_existing,
        use_ai_fallback=params.use_ai_fallback,
    )
    return schemas.CorpusClasificarResponse(**result)


@router.patch(
    "/{study_id}/corpus/{file_id}/rol",
    response_model=schemas.CorpusFileResponse,
)
async def override_corpus_rol(
    study_id: UUID,
    file_id: UUID,
    data: schemas.CorpusRolOverrideRequest,
    _: User = Depends(require_tecnico),
    db: AsyncSession = Depends(get_db),
):
    """Override manual del rol_en_corpus. Marca clasificacion_fuente='manual'."""
    from app.documents.classify_service import override_rol_manual

    corpus_file = await override_rol_manual(
        db, study_id, file_id, nuevo_rol=data.rol, notas=data.notas,
    )
    return schemas.CorpusFileResponse.model_validate(corpus_file)


# ── Datos estructurados por archivo (Sprint Drive B) ──────────────────────────

@router.get(
    "/{study_id}/corpus/{file_id}/datos",
    response_model=schemas.CorpusDatosResponse,
)
async def get_corpus_datos(
    study_id: UUID,
    file_id: UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Devuelve datos_estructurados del archivo. Si no hay, devuelve el template del rol."""
    from app.documents.structured_data import get_structured_data
    data = await get_structured_data(db, study_id, file_id)
    return schemas.CorpusDatosResponse(**data)


@router.put(
    "/{study_id}/corpus/{file_id}/datos",
    response_model=schemas.CorpusDatosUpdateResponse,
)
async def put_corpus_datos(
    study_id: UUID,
    file_id: UUID,
    data: schemas.CorpusDatosUpdateRequest,
    _: User = Depends(require_tecnico),
    db: AsyncSession = Depends(get_db),
):
    """
    Sobrescribe datos_estructurados con el JSON dado. Lo valida contra el
    esquema del rol_en_corpus (campos extra van a 'extra') y dispara el
    aplanado a corpus_extractions (legacy=false).
    """
    from app.documents.structured_data import update_structured_data
    result = await update_structured_data(db, study_id, file_id, data.datos)
    return schemas.CorpusDatosUpdateResponse(**result)


# ── Consolidado del estudio (Sprint Drive E) ──────────────────────────────────

@router.get("/{study_id}/datos-consolidados")
async def get_datos_consolidados(
    study_id: UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Devuelve el consolidado del estudio: todos los datos_estructurados de los
    archivos fusionados en una estructura espejo del informe FASE 3, con
    overrides manuales aplicados.
    """
    from app.reports.consolidator import consolidate_study_with_overrides
    consolidated = await consolidate_study_with_overrides(db, study_id)
    return consolidated


@router.put(
    "/{study_id}/consolidacion/overrides",
    response_model=schemas.ConsolidadoOverrideResponse,
)
async def set_consolidacion_overrides(
    study_id: UUID,
    data: schemas.ConsolidadoOverrideRequest,
    _: User = Depends(require_tecnico),
    db: AsyncSession = Depends(get_db),
):
    """
    Aplica overrides manuales sobre el consolidado. Cada override identifica
    un path con dot-notation (ej. 'poblacion.personas') y un valor a fijar.
    El consolidado los usa al servir GET /datos-consolidados.

    Si merge=true (default), se mezclan con los existentes; si false, reemplazan.
    """
    from app.studies.service import get_study_or_404
    study = await get_study_or_404(db, study_id)

    existing = (study.consolidacion_overrides or {}) if data.merge else {}
    for item in data.overrides:
        existing[item.path] = {
            "valor": item.valor,
            "fuente": "manual",
            "nota": item.nota,
        }
    study.consolidacion_overrides = existing
    await db.flush()
    return schemas.ConsolidadoOverrideResponse(
        study_id=str(study_id),
        overrides=existing,
        total=len(existing),
    )


@router.delete("/{study_id}/consolidacion/overrides", status_code=204)
async def clear_consolidacion_overrides(
    study_id: UUID,
    path: str | None = Query(None, description="Si se pasa, elimina solo ese path; si no, limpia todos"),
    _: User = Depends(require_tecnico),
    db: AsyncSession = Depends(get_db),
):
    """Elimina overrides — uno (si pasa ?path=) o todos."""
    from app.studies.service import get_study_or_404
    study = await get_study_or_404(db, study_id)
    existing = study.consolidacion_overrides or {}
    if path:
        existing.pop(path, None)
        study.consolidacion_overrides = existing
    else:
        study.consolidacion_overrides = None
    await db.flush()
    return None


@router.get("/{study_id}/corpus/{file_id}/log")
async def get_corpus_file_log(
    study_id: UUID,
    file_id: UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Devuelve el rastro completo de procesamiento de un archivo del corpus."""
    from sqlalchemy import select, func
    from app.studies.models import StudyCorpus, CorpusExtraction

    file = await db.get(StudyCorpus, file_id)
    if not file or file.study_id != study_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    count_res = await db.execute(
        select(func.count()).select_from(CorpusExtraction).where(
            CorpusExtraction.study_id == study_id,
            CorpusExtraction.fuente_archivo == file.nombre_archivo,
        )
    )
    total_extracciones = count_res.scalar_one()

    return {
        "id": str(file.id),
        "nombre_archivo": file.nombre_archivo,
        "tipo_archivo": file.tipo_archivo,
        "tamanio_bytes": file.tamanio_bytes,
        "estado": file.estado,
        "fuente_extraccion": file.fuente_extraccion,
        "texto_chars": file.texto_chars,
        "tiene_resumen": bool(file.resumen),
        "resumen": file.resumen,
        "error_msg": file.error_msg,
        "error_detalle": file.error_detalle,
        "total_extracciones_ia": total_extracciones,
        "sync_at": file.sync_at.isoformat() if file.sync_at else None,
        "procesado_en": file.procesado_en.isoformat() if file.procesado_en else None,
    }


# ── Extractions ───────────────────────────────────────────────────────────────

@router.get("/{study_id}/extractions", response_model=list[schemas.ExtractionResponse])
async def list_extractions(
    study_id: UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    extractions = await service.list_extractions(db, study_id)
    return [schemas.ExtractionResponse.model_validate(e) for e in extractions]


# ── Locations (coordenadas extraídas por IA) ──────────────────────────────────

@router.get("/{study_id}/locations", response_model=list[schemas.StudyLocationOut])
async def list_locations(
    study_id: UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    locations = await service.list_locations(db, study_id)
    return [schemas.StudyLocationOut.model_validate(loc) for loc in locations]


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
