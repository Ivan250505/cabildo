"""
Servicio de generación de informes.
Orquesta: recopilación de datos → motor GIS → builder Word → guardado en disco → BD.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.studies.models import (
    CorpusExtraction, GISResult, Report, Study, StudyCorpus
)
from app.reports.builder import build_report

settings = get_settings()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def _get_study_or_404(db: AsyncSession, study_id: UUID) -> Study:
    result = await db.execute(select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    if not study:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estudio no encontrado")
    return study


async def _next_version(db: AsyncSession, study_id: UUID) -> int:
    result = await db.execute(
        select(Report).where(Report.study_id == study_id).order_by(Report.version.desc())
    )
    last = result.scalars().first()
    return (last.version + 1) if last else 1


# ── Recopilación de datos para el informe ─────────────────────────────────────

async def _gather_extracciones(db: AsyncSession, study_id: UUID) -> list[dict]:
    result = await db.execute(
        select(CorpusExtraction).where(CorpusExtraction.study_id == study_id)
    )
    return [
        {
            "tipo_dato": e.tipo_dato,
            "valor": e.valor,
            "fuente_archivo": e.fuente_archivo,
            "confianza": float(e.confianza) if e.confianza else None,
        }
        for e in result.scalars().all()
    ]


async def _gather_gis_results(db: AsyncSession, study_id: UUID) -> list[dict]:
    result = await db.execute(
        select(GISResult).where(GISResult.study_id == study_id)
    )
    return [
        {
            "tipo_resultado": g.tipo_resultado,
            "parametros": g.parametros,
            "resultado_json": g.resultado_json,
            "archivo_path": g.archivo_path,
        }
        for g in result.scalars().all()
    ]


def _load_map_png(archivo_path: str | None) -> bytes | None:
    if not archivo_path:
        return None
    p = Path(archivo_path)
    if p.exists():
        return p.read_bytes()
    return None


# ── Generación del informe ────────────────────────────────────────────────────

async def generate_report(
    db: AsyncSession,
    study_id: UUID,
    generado_por: UUID,
    parametros: dict | None = None,
) -> Report:
    """
    Genera el informe Word de un estudio y crea el registro Report en BD.
    El estudio debe estar en estado 'listo_revision' o 'en_revision'.
    """
    study = await _get_study_or_404(db, study_id)

    if study.estado not in ("listo_revision", "en_revision", "corpus_ok"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se puede generar el informe en estado '{study.estado}'.",
        )

    # Recopilar datos
    extracciones = await _gather_extracciones(db, study_id)
    gis_results = await _gather_gis_results(db, study_id)

    # Cargar imágenes de mapas desde disco
    mapa_general_png: bytes | None = None
    mapas_por_capa: dict[str, bytes] = {}

    for gr in gis_results:
        tipo = gr.get("tipo_resultado", "")
        png = _load_map_png(gr.get("archivo_path"))
        if png:
            if tipo == "mapa_general":
                mapa_general_png = png
            elif tipo.startswith("mapa_capa_"):
                nombre_capa = tipo.replace("mapa_capa_", "")
                mapas_por_capa[nombre_capa] = png

    # Construir el Word
    study_dict = {
        "nombre_comunidad": study.nombre_comunidad,
        "pueblo_indigena": study.pueblo_indigena,
        "municipio": study.municipio,
        "departamento": study.departamento,
        "vereda": study.vereda,
        "nit_comunidad": study.nit_comunidad,
        "contrato_referencia": study.contrato_referencia,
        "notas_adicionales": study.notas_adicionales,
        "buffer_metros": study.buffer_metros,
    }

    docx_bytes = build_report(
        study_data=study_dict,
        extracciones=extracciones,
        gis_results=gis_results,
        mapa_general_png=mapa_general_png,
        mapas_por_capa_png=mapas_por_capa if mapas_por_capa else None,
    )

    # Guardar en disco
    version = await _next_version(db, study_id)
    out_dir = Path(settings.FILES_BASE_PATH) / str(study_id) / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = f"Informe_{study.nombre_comunidad.replace(' ', '_')}_v{version}.docx"
    out_path = out_dir / filename
    out_path.write_bytes(docx_bytes)

    # Crear registro en BD
    report = Report(
        study_id=study_id,
        version=version,
        estado="listo_revision",
        archivo_docx=str(out_path),
        hash_docx=_sha256(docx_bytes),
        generado_por=generado_por,
        parametros=parametros or {},
        generado_en=datetime.now(timezone.utc),
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)
    return report


async def approve_report(
    db: AsyncSession, study_id: UUID, report_id: UUID, aprobado_por: UUID
) -> Report:
    """Marca el informe como aprobado y actualiza el estado del estudio."""
    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.study_id == study_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Informe no encontrado")
    if report.estado not in ("listo_revision", "en_revision"):
        raise HTTPException(
            status_code=409,
            detail=f"No se puede aprobar un informe en estado '{report.estado}'",
        )

    report.estado = "aprobado"
    report.aprobado_por = aprobado_por
    report.aprobado_en = datetime.now(timezone.utc)

    # Actualizar estado del estudio
    study = await _get_study_or_404(db, study_id)
    study.estado = "aprobado"

    await db.flush()
    await db.refresh(report)
    return report


async def get_report_bytes(db: AsyncSession, study_id: UUID, report_id: UUID) -> tuple[bytes, str]:
    """Retorna (bytes del .docx, nombre del archivo) para descarga."""
    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.study_id == study_id)
    )
    report = result.scalar_one_or_none()
    if not report or not report.archivo_docx:
        raise HTTPException(status_code=404, detail="Informe no encontrado o sin archivo")

    path = Path(report.archivo_docx)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Archivo del informe no encontrado en disco")

    return path.read_bytes(), path.name
