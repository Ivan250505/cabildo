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

import logging

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.studies.models import (
    CorpusExtraction, GISResult, Report, Study, StudyCorpus
)
from app.auth.models import User
from app.reports.builder import build_report, docx_to_pdf
from app.documents.ai_writer import generate_sections

logger = logging.getLogger(__name__)

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


# ── Recopilación de datos ─────────────────────────────────────────────────────

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
    return p.read_bytes() if p.exists() else None


# ── Paso 1: crear registro Report (síncrono, en el request) ──────────────────

async def start_report(
    db: AsyncSession,
    study_id: UUID,
    generado_por: UUID,
) -> Report:
    """
    Valida el estudio y crea el registro Report con estado='generando'.
    El trabajo real lo hace build_report_bg() en background.
    """
    study = await _get_study_or_404(db, study_id)

    if study.estado not in ("listo_revision", "en_revision", "corpus_ok", "procesando"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se puede generar el informe en estado '{study.estado}'.",
        )

    version = await _next_version(db, study_id)
    report = Report(
        study_id=study_id,
        version=version,
        estado="generando",
        generado_por=generado_por,
        generado_en=datetime.now(timezone.utc),
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)
    return report


# ── Paso 2: construir el Word (background task) ───────────────────────────────

async def build_report_bg(study_id: UUID, report_id: UUID) -> None:
    """
    Corre en BackgroundTask. Genera el Word, actualiza el Report en BD.
    Usa su propia sesión de BD (la del request ya está cerrada).
    """
    async with AsyncSessionLocal() as db:
        try:
            report = await db.get(Report, report_id)
            study = await db.get(Study, study_id)
            if not report or not study:
                return

            extracciones = await _gather_extracciones(db, study_id)
            gis_results = await _gather_gis_results(db, study_id)

            mapa_general_png: bytes | None = None
            mapas_por_capa: dict[str, bytes] = {}
            for gr in gis_results:
                tipo = gr.get("tipo_resultado", "")
                png = _load_map_png(gr.get("archivo_path"))
                if png:
                    if tipo == "mapa_general":
                        mapa_general_png = png
                    elif tipo.startswith("mapa_capa_"):
                        mapas_por_capa[tipo.replace("mapa_capa_", "")] = png

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

            ai_content = generate_sections(
                study_data=study_dict,
                extracciones=extracciones,
                provider=settings.AI_PROVIDER,
                api_key=settings.AI_API_KEY,
                model=settings.AI_MODEL,
            )

            docx_bytes = build_report(
                study_data=study_dict,
                extracciones=extracciones,
                gis_results=gis_results,
                mapa_general_png=mapa_general_png,
                mapas_por_capa_png=mapas_por_capa if mapas_por_capa else None,
                ai_content=ai_content,
            )

            nombre_safe = study.nombre_comunidad.replace(" ", "_")
            filename_base = f"Informe_{nombre_safe}_v{report.version}"

            # Guardar .docx localmente (efímero, disponible para descarga inmediata)
            out_dir = Path(settings.FILES_BASE_PATH) / str(study_id) / "reports"
            out_dir.mkdir(parents=True, exist_ok=True)
            docx_path = out_dir / f"{filename_base}.docx"
            docx_path.write_bytes(docx_bytes)

            report.archivo_docx = str(docx_path)
            report.hash_docx = _sha256(docx_bytes)

            # Convertir a PDF y subir a Drive FASE3/CONCEPTO/
            pdf_filename = f"{filename_base}.pdf"
            try:
                pdf_bytes = docx_to_pdf(docx_bytes)

                if study.url_drive_fase3 and report.generado_por:
                    generador = await db.get(User, report.generado_por)
                    if generador and generador.google_token:
                        from app.drive.service import upload_report_to_drive
                        file_id, web_view_link = upload_report_to_drive(
                            generador,
                            study.url_drive_fase3,
                            pdf_bytes,
                            pdf_filename,
                        )
                        report.drive_file_id = file_id
                        report.drive_url = web_view_link
                        logger.info("PDF subido a Drive: %s", web_view_link)
                    else:
                        logger.warning("Sin token Drive para usuario %s — PDF no subido", report.generado_por)
                else:
                    logger.info("Estudio sin url_drive_fase3 — PDF no subido a Drive")

            except Exception as pdf_exc:
                logger.warning("No se pudo generar/subir PDF: %s", pdf_exc)

            report.estado = "listo_revision"
            if study.estado not in ("aprobado", "exportado"):
                study.estado = "listo_revision"

            await db.commit()

        except Exception as exc:
            await db.rollback()
            async with AsyncSessionLocal() as db2:
                report2 = await db2.get(Report, report_id)
                if report2:
                    report2.estado = "error"
                    report2.error_msg = str(exc)[:500]
                    await db2.commit()


# ── Aprobar / descargar ───────────────────────────────────────────────────────

async def approve_report(
    db: AsyncSession, study_id: UUID, report_id: UUID, aprobado_por: UUID
) -> Report:
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

    study = await _get_study_or_404(db, study_id)
    study.estado = "aprobado"

    await db.flush()
    await db.refresh(report)
    return report


async def get_report_bytes(db: AsyncSession, study_id: UUID, report_id: UUID) -> tuple[bytes, str]:
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


async def list_reports(db: AsyncSession, study_id: UUID) -> list[Report]:
    result = await db.execute(
        select(Report).where(Report.study_id == study_id).order_by(Report.version.desc())
    )
    return list(result.scalars().all())
