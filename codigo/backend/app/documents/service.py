"""
Servicio de procesamiento documental.
Itera los archivos del corpus descargados, extrae texto y entidades,
y persiste los resultados como CorpusExtraction en la BD.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.config import get_settings
from app.studies.models import CorpusExtraction, Study, StudyCorpus, StudyLocation
from app.documents.extractor import process_document
from app.documents.ai_extractor import _SKIP_SUMMARY_THRESHOLD, get_ai_extractor
from app.documents.coord_parser import parse_extraction_to_location

settings = get_settings()

# Construir el extractor de IA una sola vez (None si AI_PROVIDER=none)
_ai_extractor = get_ai_extractor(
    provider=settings.AI_PROVIDER,
    api_key=settings.AI_API_KEY,
    model=settings.AI_MODEL,
)

# Extensiones procesables por el extractor de texto
_PROCESABLES = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".jpg", ".jpeg", ".png", ".heic", ".webp"}

# API key de Gemini para Vision (None si no aplica)
_GEMINI_API_KEY: str | None = (
    settings.AI_API_KEY
    if settings.AI_PROVIDER.lower() == "gemini" and settings.AI_API_KEY
    else None
)
_GEMINI_MODEL: str = settings.AI_MODEL or "gemini-2.0-flash-lite"


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

    if study.estado not in ("borrador", "corpus_ok", "sincronizando", "procesando", "listo_revision", "error"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se puede procesar el corpus en estado '{study.estado}'.",
        )

    # Si ya hay extracciones en BD y no se pide reprocesar, reutilizarlas
    if not reprocess:
        existing = await db.execute(
            select(CorpusExtraction).where(CorpusExtraction.study_id == study_id).limit(1)
        )
        if existing.scalars().first() is not None:
            if study.estado not in ("listo_revision", "aprobado", "exportado"):
                study.estado = "corpus_ok"
            await db.flush()
            logger.info("Extracciones existentes reutilizadas para estudio %s — omitiendo lectura de archivos", study_id)
            return {
                "study_id": str(study_id),
                "archivos_encontrados": 0,
                "archivos_procesables": 0,
                "archivos_procesados": 0,
                "entidades_extraidas": 0,
                "errores": [],
                "nota": "Se reutilizaron las extracciones ya guardadas en la base de datos.",
            }

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
        msg = (
            f"No hay archivos PDF/DOCX disponibles en el servidor "
            f"({len(corpus_files)} registros en BD pero ninguno existe en disco). "
            "El servidor puede haberse reiniciado y borrado los archivos temporales. "
            "Ve a la ficha del estudio, re-sincroniza el corpus desde Drive y vuelve a intentar."
        )
        study.estado = "error"
        study.error_msg = msg[:500]
        await db.flush()
        return {
            "study_id": str(study_id),
            "archivos_encontrados": len(corpus_files),
            "archivos_procesables": 0,
            "entidades_extraidas": 0,
            "errores": [msg],
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
                gemini_api_key=_GEMINI_API_KEY,
                gemini_model=_GEMINI_MODEL,
            )
        except Exception as e:
            errores.append(f"{corpus_file.nombre_archivo}: {e}")
            corpus_file.estado = "error"
            corpus_file.error_msg = str(e)
            continue

        # Sprint Drive C: spaCy NER queda detrás de un flag. Por defecto se desactiva
        # para evitar la sopa de entidades genéricas que contaminaban corpus_extractions.
        entidades = doc_result.get("entidades", []) if settings.EXTRACTION_USE_SPACY else []

        # IA: extracción estructurada adicional si hay proveedor configurado
        if _ai_extractor:
            try:
                ai_ents = _ai_extractor.extract(
                    text=doc_result.get("texto", ""),
                    filename=corpus_file.nombre_archivo,
                )
                for e in ai_ents:
                    e["fuente_archivo"] = corpus_file.nombre_archivo
                entidades = entidades + ai_ents
            except Exception as e:
                logger.error("[IA] Error extrayendo %s: %s", corpus_file.nombre_archivo, e)
                errores.append(f"[IA] {corpus_file.nombre_archivo}: {e}")

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
                legacy=True,  # Sprint Drive B: este flujo viejo marca legacy=true
            )
            db.add(extraction)

        total_entidades += len(entidades)
        corpus_file.estado = "procesado"
        corpus_file.procesado_en = now

        # Sprint Drive C: el resumen del pipeline viejo queda detrás de un flag.
        # Si EXTRACTION_USE_LEGACY_SUMMARY=true, se sigue generando para fines de preview.
        texto_doc = doc_result.get("texto", "")
        if settings.EXTRACTION_USE_LEGACY_SUMMARY and _ai_extractor and len(texto_doc) <= _SKIP_SUMMARY_THRESHOLD:
            try:
                resumen = _ai_extractor.summarize(
                    text=texto_doc,
                    filename=corpus_file.nombre_archivo,
                    rol=corpus_file.rol_en_corpus,
                )
                if resumen:
                    corpus_file.resumen = resumen[:2000]
            except Exception as e:
                logger.warning("Error generando resumen IA para %s: %s", corpus_file.nombre_archivo, e)

        archivos_ok += 1

    if archivos_ok > 0 and study.estado not in ("listo_revision", "aprobado", "exportado"):
        study.estado = "corpus_ok"
    elif archivos_ok == 0 and study.estado not in ("listo_revision", "aprobado", "exportado"):
        err = "No se pudo procesar ningún archivo. " + "; ".join(errores[:3])
        study.estado = "error"
        study.error_msg = err[:500]

    await db.flush()

    # ── Post-procesar extracciones de coordenadas → StudyLocation ─────────────
    await _save_locations_from_extractions(db, study_id)

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


async def _save_locations_from_extractions(db: AsyncSession, study_id: UUID) -> None:
    """
    Lee las extracciones de tipo coordenada_gps / plus_code / sitio_geografico
    y las convierte en registros StudyLocation, eliminando primero los anteriores.
    """
    _COORD_TIPOS = {"coordenada_gps", "plus_code", "sitio_geografico"}

    result = await db.execute(
        select(CorpusExtraction).where(
            CorpusExtraction.study_id == study_id,
            CorpusExtraction.tipo_dato.in_(_COORD_TIPOS),
        )
    )
    coord_extractions = result.scalars().all()

    if not coord_extractions:
        return

    # Eliminar ubicaciones anteriores para repoblar
    await db.execute(
        delete(StudyLocation).where(StudyLocation.study_id == study_id)
    )

    now = datetime.now(timezone.utc)
    saved = 0
    seen_coords: set[tuple[float, float]] = set()

    for ext in coord_extractions:
        loc_data = parse_extraction_to_location(
            tipo_dato=ext.tipo_dato,
            valor=ext.valor or "",
            fuente=ext.fuente_archivo,
        )
        if not loc_data:
            continue

        # Evitar duplicados exactos (mismo punto)
        key = (round(loc_data["lat"], 4), round(loc_data["lng"], 4))
        if key in seen_coords:
            continue
        seen_coords.add(key)

        db.add(StudyLocation(
            study_id=study_id,
            extraido_en=now,
            **loc_data,
        ))
        saved += 1

    if saved:
        logger.info("Guardadas %d ubicaciones geográficas para estudio %s", saved, study_id)
    await db.flush()
