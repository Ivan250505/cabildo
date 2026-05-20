"""
Servicio de datos estructurados por archivo (Sprint Drive B).

Responsabilidades:
  - validate_and_normalize: valida un JSON contra el esquema del rol, normaliza
    campos faltantes con defaults del template, deduplica listas según
    dedup_keys del esquema y mueve campos no esperados a `extra`.
  - save_structured_data: persiste el JSON normalizado en
    study_corpus.datos_estructurados y dispara el aplanado.
  - flatten_to_extractions: repuebla corpus_extractions (legacy=false) con las
    reglas de flatten del esquema. Idempotente por (study_id, fuente_archivo).
  - get_structured_data: lectura simple.

Convención: las extracciones del pipeline anterior viven con legacy=true y se
respetan; las generadas por este flujo quedan con legacy=false.
"""
from __future__ import annotations

import copy
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.documents.doc_schemas import get_schema, schema_template, schema_version
from app.studies.models import CorpusExtraction, StudyCorpus


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_path(obj: Any, path: str) -> Any:
    """Lee un valor anidado por dot-notation. None si no existe en algún tramo."""
    if obj is None or not path:
        return None
    cur: Any = obj
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        if part not in cur:
            return None
        cur = cur[part]
    return cur


def _dedup_list(items: list, keys: list[str]) -> list:
    """Deduplica una lista de dicts por la combinación de claves dadas.
    Para listas de primitivos, deduplica por valor."""
    seen: set = set()
    out: list = []
    for item in items:
        if not isinstance(item, dict):
            if item not in seen:
                seen.add(item)
                out.append(item)
            continue
        key_tuple = tuple(
            (item.get(k) if not isinstance(item.get(k), (list, dict)) else str(item.get(k)))
            for k in keys
        )
        if key_tuple not in seen:
            seen.add(key_tuple)
            out.append(item)
    return out


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


# ── Validación / normalización ────────────────────────────────────────────────

def validate_and_normalize(rol: str | None, raw_data: Any) -> tuple[dict, list[str]]:
    """
    Devuelve (datos_normalizados, warnings).

    Reglas:
      - Si raw_data no es dict, devuelve template limpio + warning.
      - Campos del raw_data que están en el template → se aceptan tal cual.
      - Campos no esperados → se mueven a 'extra' (sin perderse).
      - Campos del template ausentes en raw_data → se llenan con su default.
      - Listas con dedup_key declarado en el esquema → deduplicadas.
    """
    template = schema_template(rol)
    schema = get_schema(rol)
    warnings: list[str] = []

    if not isinstance(raw_data, dict):
        warnings.append(f"raw_data no es dict (tipo={type(raw_data).__name__})")
        return template, warnings

    normalized: dict[str, Any] = {}
    extras: dict[str, Any] = {}

    template_keys = set(template.keys())
    for key, value in raw_data.items():
        if key in template_keys:
            normalized[key] = value
        elif key == "extra" and isinstance(value, dict):
            # Si el caller ya trae un extra, lo conservamos
            extras.update(value)
        else:
            extras[key] = value
            warnings.append(f"campo fuera de esquema: {key}")

    # Rellenar defaults
    for key, default in template.items():
        if key not in normalized:
            normalized[key] = copy.deepcopy(default)

    if extras:
        existing_extra = normalized.get("extra") if isinstance(normalized.get("extra"), dict) else {}
        normalized["extra"] = {**(existing_extra or {}), **extras}

    # Aplicar dedup en listas
    for lista_field, keys in schema.get("dedup_keys", {}).items():
        val = normalized.get(lista_field)
        if isinstance(val, list) and val:
            before = len(val)
            normalized[lista_field] = _dedup_list(val, keys)
            after = len(normalized[lista_field])
            if after < before:
                warnings.append(f"{lista_field}: {before - after} duplicados removidos")

    return normalized, warnings


# ── Aplanado a corpus_extractions ─────────────────────────────────────────────

async def flatten_to_extractions(
    db: AsyncSession,
    study_id: UUID,
    file_name: str,
    datos: dict,
    rol: str | None,
) -> int:
    """
    Repuebla la tabla derivada corpus_extractions para este archivo (legacy=false).
    Idempotente: borra las extracciones legacy=false existentes con la misma
    fuente_archivo antes de insertar las nuevas.

    Returns: número de filas insertadas.
    """
    schema = get_schema(rol)
    rules = schema.get("flatten") or []

    # Borrar extracciones derivadas previas (NO toca las legacy=true)
    await db.execute(
        delete(CorpusExtraction).where(
            CorpusExtraction.study_id == study_id,
            CorpusExtraction.fuente_archivo == file_name,
            CorpusExtraction.legacy.is_(False),
        )
    )

    now = datetime.now(timezone.utc)
    inserted = 0

    for rule in rules:
        path = rule.get("path", "")
        tipo = rule.get("tipo_dato")
        if not tipo:
            continue
        valor = _get_path(datos, path)
        if _is_empty(valor) or isinstance(valor, (list, dict)):
            continue
        db.add(CorpusExtraction(
            study_id=study_id,
            tipo_dato=tipo,
            valor=str(valor)[:500],
            fuente_archivo=file_name,
            confianza=0.900,
            extraido_en=now,
            legacy=False,
        ))
        inserted += 1

    await db.flush()
    return inserted


# ── Persistencia principal ────────────────────────────────────────────────────

async def save_structured_data(
    db: AsyncSession,
    corpus_file: StudyCorpus,
    datos: dict,
    modelo: str | None = None,
) -> tuple[dict, list[str]]:
    """
    Valida datos, los guarda en study_corpus.datos_estructurados y dispara
    el aplanado a corpus_extractions. Devuelve (datos_normalizados, warnings).
    """
    rol = corpus_file.rol_en_corpus
    normalized, warnings = validate_and_normalize(rol, datos)

    corpus_file.datos_estructurados = normalized
    corpus_file.esquema_version = schema_version(rol)
    if modelo:
        corpus_file.extraido_con_modelo = modelo
    corpus_file.extraido_en_v2 = datetime.now(timezone.utc)

    await db.flush()

    try:
        inserted = await flatten_to_extractions(
            db, corpus_file.study_id, corpus_file.nombre_archivo, normalized, rol,
        )
        logger.info(
            "Aplanado %d extracciones derivadas para %s (rol=%s)",
            inserted, corpus_file.nombre_archivo, rol,
        )
    except Exception as e:
        logger.warning("Fallo aplanando extracciones para %s: %s", corpus_file.nombre_archivo, e)

    return normalized, warnings


async def get_corpus_file_or_404(
    db: AsyncSession, study_id: UUID, file_id: UUID,
) -> StudyCorpus:
    result = await db.execute(
        select(StudyCorpus).where(
            StudyCorpus.id == file_id,
            StudyCorpus.study_id == study_id,
        )
    )
    cf = result.scalar_one_or_none()
    if not cf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archivo no encontrado")
    return cf


async def get_structured_data(
    db: AsyncSession, study_id: UUID, file_id: UUID,
) -> dict:
    """Lectura para el endpoint GET. Devuelve metadata + datos."""
    cf = await get_corpus_file_or_404(db, study_id, file_id)
    return {
        "file_id": str(cf.id),
        "study_id": str(cf.study_id),
        "nombre_archivo": cf.nombre_archivo,
        "rol_en_corpus": cf.rol_en_corpus,
        "esquema_version": cf.esquema_version,
        "extraido_con_modelo": cf.extraido_con_modelo,
        "extraido_en": cf.extraido_en_v2.isoformat() if cf.extraido_en_v2 else None,
        "hash_sha256": cf.hash_sha256,
        "tiene_datos": cf.datos_estructurados is not None,
        "datos_estructurados": cf.datos_estructurados,
        "template_si_vacio": schema_template(cf.rol_en_corpus) if cf.datos_estructurados is None else None,
    }


async def update_structured_data(
    db: AsyncSession, study_id: UUID, file_id: UUID, raw_data: dict,
) -> dict:
    """Lectura para el endpoint PUT — edita manualmente el JSON."""
    cf = await get_corpus_file_or_404(db, study_id, file_id)
    normalized, warnings = await save_structured_data(db, cf, raw_data, modelo="manual_edit")
    return {
        "file_id": str(cf.id),
        "datos_estructurados": normalized,
        "warnings": warnings,
        "esquema_version": cf.esquema_version,
    }


# ── Hash SHA256 utility (preparación para Sprint F) ───────────────────────────

def compute_file_hash(path: str | Path, chunk_size: int = 65536) -> str | None:
    """SHA256 hex digest del archivo. None si no se puede leer."""
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(chunk_size):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        logger.warning("Hash SHA256 falló para %s: %s", path, e)
        return None
