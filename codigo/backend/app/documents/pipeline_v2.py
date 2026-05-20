"""
Pipeline v2 (Sprint Drive C) — orquesta el flujo nuevo:

  1. Clasifica los archivos que no tengan rol_en_corpus aún (usa el classifier
     del Sprint Drive A).
  2. Extrae texto del archivo (cascada local + OCR + Vision del extractor
     existente, sin tocar la cascada).
  3. Llama al extractor dirigido por rol (Sprint Drive C / extractor_runner)
     que produce un único JSON estructurado por archivo.
  4. Valida + guarda en study_corpus.datos_estructurados y repuebla las
     extracciones derivadas (Sprint Drive B / structured_data).
  5. Marca el archivo como 'procesado' y calcula su SHA256 (preparación
     Sprint Drive F).

A diferencia del pipeline antiguo (app/documents/service.py::process_study_corpus):
  - NO acumula extend() de chunks.
  - NO usa spaCy NER por defecto (configurable con EXTRACTION_USE_SPACY).
  - NO genera el resumen IA viejo (queda detrás de un flag opcional).
  - NO inserta filas planas en corpus_extractions de manera directa — usa el
    flatten del Sprint B.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.config import get_settings
from app.documents.ai_extractor import get_ai_extractor
from app.documents.classifier import classify_file
from app.documents.excel_parser import parse_excel_for_role
from app.documents.extractor import extract_text_with_source
from app.documents.extractor_prompts import ROLES_CON_EXTRACTOR, ROLES_SIN_IA
from app.documents.extractor_runner import extract_for_role
from app.documents.mdb_handler import get_mdb_block_message, is_mdb
from app.documents.pdf_pages import extract_pdf_text_selective
from app.documents.photo_extractor import extract_photo_data
from app.documents.structured_data import compute_file_hash, save_structured_data
from app.studies.models import Study, StudyCorpus, StudyLocation

settings = get_settings()

# Extensiones procesables por la cascada de texto
_PROCESABLES = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".md", ".txt",
                ".jpg", ".jpeg", ".png", ".heic", ".webp"}

# Gemini API key para Vision (cuando aplica)
_GEMINI_API_KEY: str | None = (
    settings.AI_API_KEY
    if settings.AI_PROVIDER.lower() == "gemini" and settings.AI_API_KEY
    else None
)
_GEMINI_MODEL: str = settings.AI_MODEL or "gemini-2.0-flash-lite"


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_study_or_404(db: AsyncSession, study_id: UUID) -> Study:
    result = await db.execute(select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    if not study:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estudio no encontrado")
    return study


def _necesita_clasificar(f: StudyCorpus) -> bool:
    return not f.rol_en_corpus or not f.clasificacion_fuente


def _es_procesable_con_ia(f: StudyCorpus) -> bool:
    """Verdadero si el archivo debe pasar por el extractor dirigido IA."""
    if not f.ruta_local:
        return False
    p = Path(f.ruta_local)
    if not p.exists():
        return False
    if p.suffix.lower() not in _PROCESABLES:
        return False
    if f.rol_en_corpus in ROLES_SIN_IA:
        return False
    return True


# ── Pipeline principal ────────────────────────────────────────────────────────

async def process_study_corpus_v2(
    db: AsyncSession,
    study_id: UUID,
    reprocess: bool = False,
) -> dict:
    """
    Procesa el corpus de un estudio con el pipeline v2.

    Args:
        reprocess: Si True, reprocesa también archivos que ya tengan
            datos_estructurados. Si False, salta los ya procesados.

    Returns:
        Resumen con conteos y errores por archivo.
    """
    study = await _get_study_or_404(db, study_id)

    # Estados aceptados para arrancar
    if study.estado in ("aprobado", "exportado"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se puede procesar el corpus en estado '{study.estado}'.",
        )

    result = await db.execute(
        select(StudyCorpus).where(StudyCorpus.study_id == study_id)
    )
    files = list(result.scalars().all())

    if not files:
        return _empty_summary(study_id)

    ai_extractor = get_ai_extractor(
        provider=settings.AI_PROVIDER,
        api_key=settings.AI_API_KEY,
        model=settings.AI_MODEL,
    )

    summary = {
        "study_id": str(study_id),
        "total": len(files),
        "clasificados_inline": 0,
        "procesados_ia": 0,
        "saltados_sin_ia": 0,
        "saltados_ya_procesados": 0,
        "errores": [],
        "llamadas_ia_totales": 0,
        "modelo_usado": getattr(ai_extractor, "_model", None) or getattr(ai_extractor, "_model_name", None) if ai_extractor else None,
        "por_archivo": [],
    }

    if not ai_extractor:
        summary["errores"].append("AI_PROVIDER no configurado — no se puede ejecutar la extracción dirigida.")
        return summary

    for f in files:
        archivo_resumen: dict = {
            "file_id": str(f.id),
            "nombre": f.nombre_archivo,
            "rol": f.rol_en_corpus,
            "estado": None,
            "llamadas_ia": 0,
            "modo": None,
            "error": None,
        }

        # ── Clasificar si falta ──────────────────────────────────────────────
        if _necesita_clasificar(f):
            text_sample = _extract_text_sample(f)
            cr = classify_file(
                file_name=f.nombre_archivo,
                subfolder=f.fase,
                text_sample=text_sample,
                ai_extractor=ai_extractor,
            )
            f.rol_en_corpus = cr.rol
            f.clasificacion_fuente = cr.fuente
            f.clasificacion_confianza = round(cr.confianza, 3)
            f.notas_clasificacion = cr.notas
            if f.estado == "descargado" and cr.confianza >= 0.80:
                f.estado = "clasificado"
            summary["clasificados_inline"] += 1
            archivo_resumen["rol"] = cr.rol

        # ── Saltar si ya está procesado y no se pide reprocesar ──────────────
        if not reprocess and f.datos_estructurados is not None:
            archivo_resumen["estado"] = "ya_procesado"
            summary["saltados_ya_procesados"] += 1
            summary["por_archivo"].append(archivo_resumen)
            continue

        # ── Saltar archivos sin IA (geopackage, fotos sin texto, etc.) ──────
        if f.rol_en_corpus in ROLES_SIN_IA:
            archivo_resumen["estado"] = "sin_ia"
            summary["saltados_sin_ia"] += 1
            summary["por_archivo"].append(archivo_resumen)
            continue

        # ── Tipos especiales (Sprint Drive D) ────────────────────────────────
        ext = Path(f.ruta_local).suffix.lower() if f.ruta_local else ""

        # MDB / Access: bloqueo limpio
        if f.ruta_local and is_mdb(f.ruta_local):
            f.estado = "error"
            f.fuente_extraccion = "mdb_no_convertible"
            f.error_msg = get_mdb_block_message()[:500]
            archivo_resumen["estado"] = "mdb_bloqueado"
            archivo_resumen["error"] = get_mdb_block_message()
            summary["por_archivo"].append(archivo_resumen)
            continue

        # Fotos: EXIF + Vision corta
        if ext in (".jpg", ".jpeg", ".png", ".heic", ".webp"):
            datos_foto, metodo_foto = extract_photo_data(
                f.ruta_local, f.rol_en_corpus,
                gemini_api_key=_GEMINI_API_KEY, gemini_model=_GEMINI_MODEL,
            )
            f.fuente_extraccion = metodo_foto
            archivo_resumen["modo"] = metodo_foto
            if datos_foto is None:
                archivo_resumen["estado"] = "foto_sin_datos"
                archivo_resumen["error"] = "foto sin EXIF GPS y sin descripción Vision"
                summary["por_archivo"].append(archivo_resumen)
                continue
            try:
                await save_structured_data(db, f, datos_foto, modelo=metodo_foto)
                _save_location_from_photo(db, f.study_id, datos_foto, f.nombre_archivo)
            except Exception as e:
                archivo_resumen["estado"] = "error_guardado"
                archivo_resumen["error"] = str(e)
                summary["errores"].append(f"{f.nombre_archivo}: guardado falló: {e}")
                summary["por_archivo"].append(archivo_resumen)
                continue
            if not f.hash_sha256:
                f.hash_sha256 = compute_file_hash(f.ruta_local)
            f.estado = "procesado"
            f.procesado_en = datetime.now(timezone.utc)
            f.error_msg = None
            archivo_resumen["estado"] = "ok"
            summary["procesados_ia"] += 1
            summary["por_archivo"].append(archivo_resumen)
            continue

        # Excel con rol tabular: sin IA, mapping directo a esquema
        if ext in (".xlsx", ".xls"):
            datos_excel = parse_excel_for_role(f.ruta_local, f.rol_en_corpus)
            if datos_excel is not None:
                f.fuente_extraccion = "excel_tabla"
                archivo_resumen["modo"] = "excel_tabla"
                try:
                    await save_structured_data(db, f, datos_excel, modelo="excel_tabla")
                except Exception as e:
                    archivo_resumen["estado"] = "error_guardado"
                    archivo_resumen["error"] = str(e)
                    summary["errores"].append(f"{f.nombre_archivo}: guardado falló: {e}")
                    summary["por_archivo"].append(archivo_resumen)
                    continue
                if not f.hash_sha256:
                    f.hash_sha256 = compute_file_hash(f.ruta_local)
                f.estado = "procesado"
                f.procesado_en = datetime.now(timezone.utc)
                f.error_msg = None
                archivo_resumen["estado"] = "ok"
                summary["procesados_ia"] += 1
                summary["por_archivo"].append(archivo_resumen)
                continue
            # Si el Excel no es tabular reconocible → cae al flujo IA con texto plano

        if not _es_procesable_con_ia(f):
            archivo_resumen["estado"] = "no_procesable"
            archivo_resumen["error"] = "archivo no disponible o formato no soportado"
            summary["por_archivo"].append(archivo_resumen)
            continue

        # ── Extraer texto ────────────────────────────────────────────────────
        try:
            if ext == ".pdf":
                text, fuente_text, _meta_pdf = extract_pdf_text_selective(
                    f.ruta_local,
                    gemini_api_key=_GEMINI_API_KEY, gemini_model=_GEMINI_MODEL,
                )
                error_text = None
            else:
                text, fuente_text, error_text = extract_text_with_source(
                    f.ruta_local,
                    gemini_api_key=_GEMINI_API_KEY, gemini_model=_GEMINI_MODEL,
                )
            f.fuente_extraccion = fuente_text
            f.texto_chars = len(text or "")
            if error_text:
                f.error_detalle = error_text
        except Exception as e:
            archivo_resumen["estado"] = "error_extraccion_texto"
            archivo_resumen["error"] = str(e)
            f.error_msg = str(e)[:500]
            summary["errores"].append(f"{f.nombre_archivo}: {e}")
            summary["por_archivo"].append(archivo_resumen)
            continue

        if not text or not text.strip():
            archivo_resumen["estado"] = "sin_texto"
            archivo_resumen["error"] = (error_text if 'error_text' in locals() else None) or "el archivo no produjo texto"
            summary["por_archivo"].append(archivo_resumen)
            continue

        # ── Extracción dirigida por rol ─────────────────────────────────────
        datos_ia, meta = extract_for_role(
            text=text,
            filename=f.nombre_archivo,
            rol=f.rol_en_corpus,
            ai_extractor=ai_extractor,
        )
        archivo_resumen["llamadas_ia"] = meta.get("llamadas_ia", 0)
        archivo_resumen["modo"] = meta.get("modo")
        summary["llamadas_ia_totales"] += meta.get("llamadas_ia", 0)

        if datos_ia is None:
            archivo_resumen["estado"] = "error_ia"
            archivo_resumen["error"] = meta.get("error") or "respuesta IA vacía"
            f.error_msg = (meta.get("error") or "extracción IA falló")[:500]
            summary["errores"].append(f"{f.nombre_archivo}: {archivo_resumen['error']}")
            summary["por_archivo"].append(archivo_resumen)
            continue

        # ── Guardar via Sprint B (valida + flatten) ─────────────────────────
        try:
            await save_structured_data(
                db, f, datos_ia, modelo=meta.get("modelo"),
            )
        except Exception as e:
            archivo_resumen["estado"] = "error_guardado"
            archivo_resumen["error"] = str(e)
            summary["errores"].append(f"{f.nombre_archivo}: guardado falló: {e}")
            summary["por_archivo"].append(archivo_resumen)
            continue

        # ── Hash SHA256 (preparación Sprint F) ──────────────────────────────
        if not f.hash_sha256 and f.ruta_local:
            f.hash_sha256 = compute_file_hash(f.ruta_local)

        f.estado = "procesado"
        f.procesado_en = datetime.now(timezone.utc)
        f.error_msg = None

        archivo_resumen["estado"] = "ok"
        summary["procesados_ia"] += 1
        summary["por_archivo"].append(archivo_resumen)

    # ── Actualizar estado del estudio ─────────────────────────────────────────
    if summary["procesados_ia"] > 0 and study.estado not in ("listo_revision", "aprobado", "exportado"):
        study.estado = "corpus_ok"
    elif summary["procesados_ia"] == 0 and summary["errores"] and study.estado not in ("listo_revision", "aprobado", "exportado"):
        study.estado = "error"
        study.error_msg = ("; ".join(summary["errores"][:2]))[:500]

    await db.flush()
    return summary


# ── Helpers internos ──────────────────────────────────────────────────────────

def _extract_text_sample(corpus_file: StudyCorpus, max_chars: int = 4000) -> str | None:
    """Devuelve los primeros caracteres del texto local (sin OCR) para clasificación."""
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
            return None
        return (text or "")[:max_chars] or None
    except Exception:
        return None


def _empty_summary(study_id: UUID) -> dict:
    return {
        "study_id": str(study_id),
        "total": 0,
        "clasificados_inline": 0,
        "procesados_ia": 0,
        "saltados_sin_ia": 0,
        "saltados_ya_procesados": 0,
        "errores": [],
        "llamadas_ia_totales": 0,
        "modelo_usado": None,
        "por_archivo": [],
    }


def _save_location_from_photo(
    db: AsyncSession,
    study_id: UUID,
    datos_foto: dict,
    nombre_archivo: str,
) -> None:
    """Crea un StudyLocation si la foto trae coordenadas (EXIF o Vision)."""
    ubic = datos_foto.get("ubicacion_sugerida")
    if not isinstance(ubic, dict):
        return
    lat = ubic.get("lat")
    lng = ubic.get("lng")
    if lat is None or lng is None:
        return
    try:
        db.add(StudyLocation(
            study_id=study_id,
            nombre=ubic.get("nombre") or Path(nombre_archivo).stem,
            tipo=ubic.get("tipo") or "punto_geografico",
            lat=float(lat),
            lng=float(lng),
            descripcion=ubic.get("descripcion"),
            fuente_archivo=nombre_archivo,
            confianza=0.95,
        ))
        logger.info("StudyLocation creado desde foto %s (%s, %s)", nombre_archivo, lat, lng)
    except Exception as e:
        logger.warning("No se pudo crear StudyLocation desde %s: %s", nombre_archivo, e)
