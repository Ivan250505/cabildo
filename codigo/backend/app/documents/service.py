"""
Servicio de procesamiento documental.
Itera los archivos del corpus descargados, extrae texto y entidades,
y persiste los resultados como CorpusExtraction en la BD.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.studies.models import CorpusExtraction, Study, StudyCorpus
from app.documents.extractor import process_document

settings = get_settings()

# Extensiones procesables por el extractor de texto
_PROCESABLES = {".pdf", ".docx", ".doc"}


async def _get_study_or_404(db: AsyncSession, study_id: UUID) -> Study:
    result = await db.execute(select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    if not study:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estudio no encontrado")
    return study


async def process_study_corpus(
    db: AsyncSession,
    study_id: UUID,
    reprocess: bool = False,
) -> dict:
    """
    Procesa todos los archivos de texto del corpus de un estudio.
    Extrae entidades NLP y cifras de población, guardando CorpusExtraction.

    Args:
        reprocess: Si True, elimina las extracciones anteriores y reprocesa todo.
    """
    study = await _get_study_or_404(db, study_id)

    if study.estado not in ("corpus_ok", "sincronizando", "procesando", "listo_revision", "error"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se puede procesar el corpus en estado '{study.estado}'.",
        )

    # Obtener archivos descargados
    result = await db.execute(
        select(StudyCorpus).where(
            StudyCorpus.study_id == study_id,
            StudyCorpus.estado == "descargado",
        )
    )
    corpus_files = list(result.scalars().all())

    procesables = [
        f for f in corpus_files
        if f.ruta_local and Path(f.ruta_local).suffix.lower() in _PROCESABLES
        and Path(f.ruta_local).exists()
    ]

    if not procesables:
        return {
            "study_id": str(study_id),
            "archivos_encontrados": len(corpus_files),
            "archivos_procesables": 0,
            "entidades_extraidas": 0,
            "errores": ["No hay archivos de texto descargados (PDF/DOCX) para procesar."],
        }

    # Eliminar extracciones previas si se reprocesa
    if reprocess:
        await db.execute(
            delete(CorpusExtraction).where(CorpusExtraction.study_id == study_id)
        )

    errores: list[str] = []
    total_entidades = 0
    archivos_ok = 0

    for corpus_file in procesables:
        path = Path(corpus_file.ruta_local)
        try:
            doc_result = process_document(
                path,
                source_name=corpus_file.nombre_archivo,
                model_name=settings.SPACY_MODEL,
            )
        except Exception as e:
            errores.append(f"{corpus_file.nombre_archivo}: {e}")
            corpus_file.estado = "error"
            corpus_file.error_msg = str(e)
            continue

        entidades = doc_result.get("entidades", [])
        now = datetime.now(timezone.utc)

        for ent in entidades:
            valor = ent.get("valor", "")
            if not valor or len(valor.strip()) < 2:
                continue
            extraction = CorpusExtraction(
                study_id=study_id,
                tipo_dato=ent.get("tipo_dato", "desconocido"),
                valor=valor.strip()[:500],
                fuente_archivo=ent.get("fuente_archivo", corpus_file.nombre_archivo),
                confianza=ent.get("confianza"),
                extraido_en=now,
            )
            db.add(extraction)

        total_entidades += len(entidades)
        corpus_file.estado = "procesado"
        corpus_file.procesado_en = now
        archivos_ok += 1

    # Si hay al menos un archivo procesado correctamente → corpus_ok
    if archivos_ok > 0 and study.estado not in ("listo_revision", "aprobado", "exportado"):
        study.estado = "corpus_ok"

    await db.flush()

    return {
        "study_id": str(study_id),
        "archivos_encontrados": len(corpus_files),
        "archivos_procesables": len(procesables),
        "archivos_procesados": archivos_ok,
        "entidades_extraidas": total_entidades,
        "errores": errores,
    }


async def get_extraction_summary(db: AsyncSession, study_id: UUID) -> dict:
    """Resumen de las extracciones agrupadas por tipo_dato."""
    await _get_study_or_404(db, study_id)

    result = await db.execute(
        select(CorpusExtraction).where(CorpusExtraction.study_id == study_id)
    )
    extracciones = result.scalars().all()

    by_tipo: dict[str, list[str]] = {}
    for e in extracciones:
        by_tipo.setdefault(e.tipo_dato, []).append(e.valor or "")

    return {
        "study_id": str(study_id),
        "total_extracciones": len(extracciones),
        "por_tipo": {tipo: vals[:20] for tipo, vals in by_tipo.items()},
    }
