"""Generador de PDF parametrizado para cualquier encuesta del catálogo.

Toma una `SurveyResponse` y su `SurveyType` (con secciones + preguntas) y produce
un PDF estructurado: portada → secciones → preguntas con sus respuestas.

Dependencia: fpdf2 (puro Python, sin binarios externos).
"""
from __future__ import annotations

import io
from datetime import datetime
from uuid import UUID

from fpdf import FPDF
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.studies.models import Study
from app.surveys.models import (
    SurveyAnswer, SurveyJournalEntry, SurveyPerson, SurveyQuestion, SurveyResponse,
    SurveySection, SurveyType,
)


# ── Colores ─────────────────────────────────────────────────────────────────────

COLOR_AZUL = (26, 58, 92)
COLOR_DORADO = (200, 146, 42)
COLOR_GRIS = (110, 110, 110)
COLOR_GRIS_CLARO = (235, 235, 235)
COLOR_NEGRO = (26, 26, 26)
COLOR_BORRADOR = (200, 200, 200)


# ── PDF base con encabezado/pie ────────────────────────────────────────────────

class SurveyPDF(FPDF):
    def __init__(self, titulo_encuesta: str, nombre_comunidad: str, es_borrador: bool):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.titulo_encuesta = titulo_encuesta
        self.nombre_comunidad = nombre_comunidad
        self.es_borrador = es_borrador
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(left=18, top=22, right=18)

    def header(self) -> None:
        # Línea dorada superior
        self.set_draw_color(*COLOR_DORADO)
        self.set_line_width(0.6)
        self.line(18, 14, self.w - 18, 14)
        # Texto del encabezado
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*COLOR_AZUL)
        self.set_xy(18, 8)
        self.cell(0, 4, "EtnIA — Plataforma de Análisis Etnográfico", align="L")
        self.set_xy(18, 8)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*COLOR_GRIS)
        self.cell(0, 4, self.titulo_encuesta, align="R")
        # Marca de agua si es borrador
        if self.es_borrador:
            self.set_font("Helvetica", "B", 60)
            self.set_text_color(*COLOR_BORRADOR)
            # Centrado aproximado en diagonal — fpdf2 soporta rotate via with_rotation context
            with self.rotation(45, self.w / 2, self.h / 2):
                self.set_xy(self.w / 2 - 50, self.h / 2 - 10)
                self.cell(100, 20, "BORRADOR", align="C")
            self.set_text_color(*COLOR_NEGRO)

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*COLOR_GRIS)
        fecha = datetime.utcnow().strftime("%Y-%m-%d")
        self.cell(0, 4, f"Generado por EtnIA · {self.nombre_comunidad} · {fecha}", align="L")
        self.cell(0, 4, f"Página {self.page_no()}/{{nb}}", align="R")


# ── Helpers de renderizado ─────────────────────────────────────────────────────

def _sanitize(text: str | None) -> str:
    """fpdf2 con fuente core acepta Latin-1; reemplaza caracteres fuera de rango."""
    if text is None:
        return ""
    return str(text).encode("latin-1", "replace").decode("latin-1")


def _label(pdf: SurveyPDF, text: str) -> None:
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*COLOR_AZUL)
    pdf.multi_cell(0, 5, _sanitize(text))


def _valor(pdf: SurveyPDF, text: str, italic: bool = False) -> None:
    pdf.set_font("Helvetica", "I" if italic else "", 10)
    pdf.set_text_color(*(COLOR_GRIS if italic else COLOR_NEGRO))
    pdf.multi_cell(0, 5, _sanitize(text or "(no diligenciado)"))
    pdf.ln(1)


def _seccion_titulo(pdf: SurveyPDF, titulo: str, descripcion: str | None) -> None:
    if pdf.get_y() > pdf.h - 50:
        pdf.add_page()
    pdf.ln(3)
    pdf.set_fill_color(*COLOR_AZUL)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, _sanitize(titulo), fill=True, new_x="LMARGIN", new_y="NEXT")
    if descripcion:
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(*COLOR_GRIS)
        pdf.multi_cell(0, 5, _sanitize(descripcion))
    pdf.ln(2)


def _format_value(question: SurveyQuestion, ans: SurveyAnswer | None) -> str:
    if not ans:
        return ""
    tipo = question.tipo_dato
    if tipo == "number":
        return f"{ans.valor_numero:g}" if ans.valor_numero is not None else ""
    if tipo == "date":
        return ans.valor_fecha.strftime("%Y-%m-%d") if ans.valor_fecha else ""
    if tipo == "boolean":
        return "Sí" if ans.valor_bool else "No"
    if tipo == "multiselect":
        items = ans.valor_json if isinstance(ans.valor_json, list) else []
        return ", ".join(str(x) for x in items) if items else ""
    # text, textarea, select
    return ans.valor_texto or ""


def _render_table_persons(pdf: SurveyPDF, persons: list[SurveyPerson], fields: list[str]) -> None:
    if not persons:
        _valor(pdf, "(sin registros)", italic=True)
        return
    # Header
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(*COLOR_GRIS_CLARO)
    pdf.set_text_color(*COLOR_AZUL)
    col_w = (pdf.w - 36) / (len(fields) + 1)
    pdf.cell(10, 7, "#", border=1, fill=True, align="C")
    for f in fields:
        pdf.cell(col_w, 7, _sanitize(f.capitalize()), border=1, fill=True, align="L")
    pdf.ln()
    # Filas
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*COLOR_NEGRO)
    for i, p in enumerate(persons, start=1):
        pdf.cell(10, 7, str(i), border=1, align="C")
        for f in fields:
            value = getattr(p, f, None)
            pdf.cell(col_w, 7, _sanitize(str(value) if value is not None else "—"), border=1)
        pdf.ln()
    pdf.ln(2)


def _render_journal_entries(pdf: SurveyPDF, entries: list[SurveyJournalEntry]) -> None:
    if not entries:
        _valor(pdf, "(sin entradas)", italic=True)
        return
    for entry in entries:
        # Cabecera de entrada
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*COLOR_AZUL)
        fecha_str = entry.fecha.strftime("%Y-%m-%d") if entry.fecha else "(sin fecha)"
        titulo = entry.titulo or "(sin título)"
        pdf.multi_cell(0, 5, _sanitize(f"▸ {fecha_str} — {titulo}"))
        # Contenido
        if entry.contenido:
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*COLOR_NEGRO)
            pdf.multi_cell(0, 4.5, _sanitize(entry.contenido))
        # Tags
        if entry.tags:
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(*COLOR_GRIS)
            tags_str = "  ·  ".join(f"#{t}" for t in entry.tags)
            pdf.multi_cell(0, 4, _sanitize(tags_str))
        pdf.ln(2)


def _render_question(
    pdf: SurveyPDF,
    question: SurveyQuestion,
    answer: SurveyAnswer | None,
    persons: list[SurveyPerson],
    journal: list[SurveyJournalEntry],
) -> None:
    _label(pdf, question.label)
    if question.tipo_dato == "table_persons":
        fields = ["nombre", "documento", "cargo", "contacto"]
        if isinstance(question.validaciones, dict):
            v = question.validaciones.get("fields")
            if isinstance(v, list) and v:
                fields = [str(x) for x in v]
        _render_table_persons(pdf, persons, fields)
        return
    if question.tipo_dato == "journal_entries":
        _render_journal_entries(pdf, journal)
        return
    value = _format_value(question, answer)
    if value:
        _valor(pdf, value)
    else:
        _valor(pdf, "(no diligenciado)", italic=True)


# ── Función pública ────────────────────────────────────────────────────────────

async def generate_survey_pdf(db: AsyncSession, response_id: UUID) -> tuple[bytes, str]:
    """Genera el PDF de una response y devuelve (bytes, nombre_archivo)."""
    response = (
        await db.execute(select(SurveyResponse).where(SurveyResponse.id == response_id))
    ).scalar_one_or_none()
    if not response:
        raise ValueError(f"Response {response_id} no encontrada")

    survey_type = (await db.execute(
        select(SurveyType)
        .where(SurveyType.id == response.survey_type_id)
        .options(selectinload(SurveyType.sections).selectinload(SurveySection.questions))
    )).scalar_one()

    study = (await db.execute(select(Study).where(Study.id == response.study_id))).scalar_one()

    # Cargar answers + persons en un solo paso (mapas por question_id)
    ans_rows = (await db.execute(
        select(SurveyAnswer).where(SurveyAnswer.response_id == response_id)
    )).scalars().all()
    answers_by_q: dict[UUID, SurveyAnswer] = {a.question_id: a for a in ans_rows}

    p_rows = (await db.execute(
        select(SurveyPerson)
        .where(SurveyPerson.response_id == response_id)
        .order_by(SurveyPerson.orden)
    )).scalars().all()
    persons_by_q: dict[UUID, list[SurveyPerson]] = {}
    for p in p_rows:
        persons_by_q.setdefault(p.question_id, []).append(p)

    j_rows = (await db.execute(
        select(SurveyJournalEntry)
        .where(SurveyJournalEntry.response_id == response_id)
        .order_by(SurveyJournalEntry.orden)
    )).scalars().all()
    journal_by_q: dict[UUID, list[SurveyJournalEntry]] = {}
    for j in j_rows:
        journal_by_q.setdefault(j.question_id, []).append(j)

    es_borrador = response.estado != "completada"
    pdf = SurveyPDF(survey_type.nombre, study.nombre_comunidad, es_borrador)
    pdf.alias_nb_pages()
    pdf.add_page()

    # Portada / encabezado de documento
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*COLOR_AZUL)
    pdf.ln(4)
    pdf.multi_cell(0, 9, _sanitize(survey_type.nombre))
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*COLOR_GRIS)
    pdf.multi_cell(0, 6, _sanitize(study.nombre_comunidad))
    sub = []
    if study.pueblo_indigena:
        sub.append(study.pueblo_indigena)
    sub.append(f"{study.municipio}, {study.departamento}")
    if study.contrato_referencia:
        sub.append(f"Contrato: {study.contrato_referencia}")
    pdf.multi_cell(0, 5, _sanitize(" · ".join(sub)))
    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 9)
    estado_label = "BORRADOR" if es_borrador else "COMPLETADA"
    pdf.cell(0, 5, _sanitize(f"Estado: {estado_label}"))
    pdf.ln(8)

    # Secciones
    for sec in survey_type.sections:
        _seccion_titulo(pdf, sec.titulo, sec.descripcion)
        for q in sec.questions:
            _render_question(
                pdf, q,
                answers_by_q.get(q.id),
                persons_by_q.get(q.id, []),
                journal_by_q.get(q.id, []),
            )

    # fpdf2 returns bytearray; convertir a bytes
    raw = pdf.output(dest="S")
    if isinstance(raw, str):
        # Versiones viejas: latin-1 string
        data = raw.encode("latin-1")
    else:
        data = bytes(raw)

    filename = f"{survey_type.code}_{study.nombre_comunidad.replace(' ', '_')}.pdf"
    return data, filename
