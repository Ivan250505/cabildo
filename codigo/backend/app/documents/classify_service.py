"""
Servicio que orquesta la clasificación de archivos del corpus de un estudio.

Llama a `app.documents.classifier.classify_file` para cada archivo, persiste:
  - study_corpus.rol_en_corpus
  - study_corpus.clasificacion_fuente
  - study_corpus.clasificacion_confianza
  - study_corpus.notas_clasificacion

Si el archivo está en estado 'descargado' y la confianza ≥ umbral, lo mueve
a estado 'clasificado'.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.config import get_settings
from app.documents.ai_extractor import get_ai_extractor
from app.documents.classifier import (
    CONFIANZA, ClassificationResult, classify_file,
)
from app.documents.extractor import extract_text_with_source
from app.studies.models import Study, StudyCorpus

settings = get_settings()

# Umbral para considerar el archivo clasificado con suficiente seguridad
_CONFIANZA_OK = 0.80

# Cuántos caracteres del archivo enviamos a la IA para clasificar (extracto inicial)
_TEXT_SAMPLE_CHARS = 4000


def _extract_text_sample(corpus_file: StudyCorpus) -> str | None:
    """
    Devuelve un extracto del texto del archivo si está descargado y es procesable
    por la cascada local. NO usa OCR/Vision en este sprint para evitar consumir
    tokens en la clasificación. Si el archivo no es texto-extraíble localmente,
    devuelve None y el clasificador se queda con la heurística sin IA.
    """
    if not corpus_file.ruta_local:
        return None
    p = Path(corpus_file.ruta_local)
    if not p.exists():
        return None
    if p.suffix.lower() not in (".pdf", ".docx", ".doc", ".xlsx", ".xls", ".md", ".txt"):
        return None
    try:
        text, fuente, _ = extract_text_with_source(p, gemini_api_key=None)
        if fuente != "local":
            # Solo aceptamos texto local — sin OCR — para clasificación
            return None
        return (text or "")[:_TEXT_SAMPLE_CHARS] or None
    except Exception as e:
        logger.info("Sin extracto local para %s: %s", corpus_file.nombre_archivo, e)
        return None


def _subfolder_hint(corpus_file: StudyCorpus) -> str | None:
    """
    Pista de carpeta para el clasificador. Hoy usamos la fase + cualquier hint
    embebido en el nombre. Cuando el listador de Drive empiece a guardar la
    subcarpeta explícitamente, esto se reemplaza por corpus_file.subfolder.
    """
    return corpus_file.fase or None


async def _get_study_or_404(db: AsyncSession, study_id: UUID) -> Study:
    result = await db.execute(select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    if not study:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estudio no encontrado")
    return study


async def classify_study_corpus(
    db: AsyncSession,
    study_id: UUID,
    ignore_existing: bool = False,
    use_ai_fallback: bool = True,
) -> dict:
    """
    Clasifica todos los archivos del corpus del estudio.

    Args:
        ignore_existing: si False, salta archivos con clasificacion_fuente != None
                         (no toca lo ya clasificado, salvo manual).
                         Si True, reclasifica todo excepto los marcados como 'manual'.
        use_ai_fallback: si False, solo corre heurística (sin IA).

    Returns:
        {
            'study_id': str,
            'total_archivos': int,
            'clasificados': int,
            'omitidos': int,
            'fallback_otro': int,
            'por_fuente': {fuente: count},
            'archivos': [{file_id, nombre, rol, fuente, confianza}]
        }
    """
    await _get_study_or_404(db, study_id)

    result = await db.execute(
        select(StudyCorpus).where(StudyCorpus.study_id == study_id)
    )
    files = list(result.scalars().all())

    if not files:
        return {
            "study_id": str(study_id),
            "total_archivos": 0,
            "clasificados": 0,
            "omitidos": 0,
            "fallback_otro": 0,
            "por_fuente": {},
            "archivos": [],
        }

    ai_extractor = None
    if use_ai_fallback:
        ai_extractor = get_ai_extractor(
            provider=settings.AI_PROVIDER,
            api_key=settings.AI_API_KEY,
            model=settings.AI_MODEL,
        )

    clasificados = 0
    omitidos = 0
    fallback = 0
    por_fuente: dict[str, int] = {}
    detalle: list[dict] = []

    for f in files:
        # Respetar overrides manuales siempre
        if f.clasificacion_fuente == "manual":
            omitidos += 1
            detalle.append({
                "file_id": str(f.id),
                "nombre": f.nombre_archivo,
                "rol": f.rol_en_corpus,
                "fuente": "manual",
                "confianza": float(f.clasificacion_confianza or 1.0),
                "omitido": True,
            })
            continue

        if not ignore_existing and f.clasificacion_fuente is not None:
            omitidos += 1
            detalle.append({
                "file_id": str(f.id),
                "nombre": f.nombre_archivo,
                "rol": f.rol_en_corpus,
                "fuente": f.clasificacion_fuente,
                "confianza": float(f.clasificacion_confianza or 0.0),
                "omitido": True,
            })
            continue

        text_sample = _extract_text_sample(f) if ai_extractor else None
        subfolder = _subfolder_hint(f)

        cr: ClassificationResult = classify_file(
            file_name=f.nombre_archivo,
            subfolder=subfolder,
            text_sample=text_sample,
            ai_extractor=ai_extractor,
        )

        f.rol_en_corpus = cr.rol
        f.clasificacion_fuente = cr.fuente
        f.clasificacion_confianza = round(cr.confianza, 3)
        f.notas_clasificacion = cr.notas

        # Si el archivo estaba descargado y se clasificó con confianza ok, marcar 'clasificado'
        if f.estado == "descargado" and cr.confianza >= _CONFIANZA_OK:
            f.estado = "clasificado"

        por_fuente[cr.fuente] = por_fuente.get(cr.fuente, 0) + 1
        if cr.fuente == "fallback_otro":
            fallback += 1
        clasificados += 1

        detalle.append({
            "file_id": str(f.id),
            "nombre": f.nombre_archivo,
            "rol": cr.rol,
            "fuente": cr.fuente,
            "confianza": round(cr.confianza, 3),
            "omitido": False,
            "notas": cr.notas,
        })

    await db.flush()

    return {
        "study_id": str(study_id),
        "total_archivos": len(files),
        "clasificados": clasificados,
        "omitidos": omitidos,
        "fallback_otro": fallback,
        "por_fuente": por_fuente,
        "archivos": detalle,
    }


async def override_rol_manual(
    db: AsyncSession,
    study_id: UUID,
    file_id: UUID,
    nuevo_rol: str,
    notas: str | None = None,
) -> StudyCorpus:
    """Override manual del rol_en_corpus. Marca clasificacion_fuente='manual', confianza=1.0."""
    from app.studies.models import CORPUS_ROLES

    if nuevo_rol not in CORPUS_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rol '{nuevo_rol}' no es válido. Valores aceptados: {list(CORPUS_ROLES)}",
        )

    result = await db.execute(
        select(StudyCorpus).where(
            StudyCorpus.id == file_id,
            StudyCorpus.study_id == study_id,
        )
    )
    corpus_file = result.scalar_one_or_none()
    if not corpus_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archivo no encontrado")

    corpus_file.rol_en_corpus = nuevo_rol
    corpus_file.clasificacion_fuente = "manual"
    corpus_file.clasificacion_confianza = CONFIANZA["manual"]
    corpus_file.notas_clasificacion = notas or "Asignado manualmente por el usuario"

    if corpus_file.estado == "descargado":
        corpus_file.estado = "clasificado"

    await db.flush()
    await db.refresh(corpus_file)
    return corpus_file
