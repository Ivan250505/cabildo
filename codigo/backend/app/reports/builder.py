"""
Generador de documentos Word (.docx) para estudios etnológicos.
Produce el informe que soporta el acto administrativo del Ministerio del Interior.

Paleta institucional:
  Rojo primario   #B22222   (encabezados principales)
  Azul marino     #1A3A5C   (encabezados secundarios, tabla cabecera)
  Dorado          #C8922A   (acento, líneas decorativas)
"""
from __future__ import annotations

import io
import logging
import subprocess
import tempfile
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Emu, Inches, Pt, RGBColor

# ── Colores institucionales ───────────────────────────────────────────────────

COLOR_ROJO   = RGBColor(0xB2, 0x22, 0x22)
COLOR_AZUL   = RGBColor(0x1A, 0x3A, 0x5C)
COLOR_DORADO = RGBColor(0xC8, 0x92, 0x2A)
COLOR_NEGRO  = RGBColor(0x1A, 0x1A, 0x1A)
COLOR_GRIS   = RGBColor(0x66, 0x66, 0x66)
COLOR_BLANCO = RGBColor(0xFF, 0xFF, 0xFF)


# ── Helpers XML ───────────────────────────────────────────────────────────────

def _set_cell_bg(cell, hex_color: str) -> None:
    """Establece el color de fondo de una celda de tabla."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def _set_row_height(row, height_cm: float) -> None:
    tr = row._tr
    trPr = tr.get_or_add_trPr()
    trHeight = OxmlElement("w:trHeight")
    trHeight.set(qn("w:val"), str(int(Cm(height_cm).emu / 914.4)))
    trHeight.set(qn("w:hRule"), "exact")
    trPr.append(trHeight)


def _add_horizontal_rule(doc: Document, color: RGBColor = COLOR_DORADO) -> None:
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), str(color))
    pBdr.append(bottom)
    pPr.append(pBdr)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(4)


def _page_break(doc: Document) -> None:
    doc.add_page_break()


# ── Estilos de párrafo ────────────────────────────────────────────────────────

def _heading1(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(text.upper())
    run.bold = True
    run.font.size = Pt(14)
    run.font.color.rgb = COLOR_ROJO
    run.font.name = "Calibri"
    _add_horizontal_rule(doc, COLOR_ROJO)


def _heading2(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(12)
    run.font.color.rgb = COLOR_AZUL
    run.font.name = "Calibri"


def _heading3(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(11)
    run.font.color.rgb = COLOR_DORADO
    run.font.name = "Calibri"


def _body(doc: Document, text: str, italic: bool = False) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.first_line_indent = Cm(0.75)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    run = p.add_run(text)
    run.font.size = Pt(11)
    run.font.color.rgb = COLOR_NEGRO
    run.font.name = "Calibri"
    run.italic = italic


def _label_value(doc: Document, label: str, value: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(3)
    r1 = p.add_run(f"{label}: ")
    r1.bold = True
    r1.font.size = Pt(11)
    r1.font.color.rgb = COLOR_AZUL
    r1.font.name = "Calibri"
    r2 = p.add_run(value or "—")
    r2.font.size = Pt(11)
    r2.font.color.rgb = COLOR_NEGRO
    r2.font.name = "Calibri"


# ── Tablas ────────────────────────────────────────────────────────────────────

def _info_table(doc: Document, rows: list[tuple[str, str]]) -> None:
    """Tabla de dos columnas: etiqueta | valor, con cabecera azul marino."""
    table = doc.add_table(rows=1 + len(rows), cols=2)
    table.style = "Table Grid"
    table.columns[0].width = Cm(6)
    table.columns[1].width = Cm(10)

    # Cabecera
    hdr = table.rows[0]
    for i, txt in enumerate(["Campo", "Valor"]):
        cell = hdr.cells[i]
        cell.text = txt
        _set_cell_bg(cell, "1A3A5C")
        run = cell.paragraphs[0].runs[0]
        run.bold = True
        run.font.color.rgb = COLOR_BLANCO
        run.font.size = Pt(10)

    for idx, (label, value) in enumerate(rows, start=1):
        row = table.rows[idx]
        row.cells[0].text = label
        row.cells[1].text = value or "—"
        row.cells[0].paragraphs[0].runs[0].font.size = Pt(10)
        row.cells[1].paragraphs[0].runs[0].font.size = Pt(10)
        if idx % 2 == 0:
            _set_cell_bg(row.cells[0], "F5F5F5")
            _set_cell_bg(row.cells[1], "F5F5F5")


def _matrix_table(doc: Document, headers: list[str], data: list[list[str]]) -> None:
    """Tabla genérica de resultados SIG."""
    table = doc.add_table(rows=1 + len(data), cols=len(headers))
    table.style = "Table Grid"

    hdr = table.rows[0]
    for i, h in enumerate(headers):
        cell = hdr.cells[i]
        cell.text = h
        _set_cell_bg(cell, "1A3A5C")
        run = cell.paragraphs[0].runs[0]
        run.bold = True
        run.font.color.rgb = COLOR_BLANCO
        run.font.size = Pt(9)

    for r_idx, row_data in enumerate(data, start=1):
        row = table.rows[r_idx]
        for c_idx, val in enumerate(row_data):
            row.cells[c_idx].text = str(val)
            row.cells[c_idx].paragraphs[0].runs[0].font.size = Pt(9)
            if r_idx % 2 == 0:
                _set_cell_bg(row.cells[c_idx], "EEF2F7")


# ── Portada ───────────────────────────────────────────────────────────────────

def _add_portada(doc: Document, study_data: dict) -> None:
    # Espacio superior
    for _ in range(4):
        doc.add_paragraph()

    # Título institucional
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("MINISTERIO DEL INTERIOR")
    run.bold = True
    run.font.size = Pt(16)
    run.font.color.rgb = COLOR_AZUL
    run.font.name = "Calibri"

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = p2.add_run("Dirección de Asuntos Indígenas, ROM y Minorías")
    r2.font.size = Pt(12)
    r2.font.color.rgb = COLOR_GRIS
    r2.font.name = "Calibri"

    doc.add_paragraph()
    _add_horizontal_rule(doc, COLOR_DORADO)
    doc.add_paragraph()

    # Título del informe
    p3 = doc.add_paragraph()
    p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r3 = p3.add_run("ESTUDIO ETNOLÓGICO PARA EL RECONOCIMIENTO\nDE COMUNIDAD INDÍGENA")
    r3.bold = True
    r3.font.size = Pt(18)
    r3.font.color.rgb = COLOR_ROJO
    r3.font.name = "Calibri"

    doc.add_paragraph()

    # Nombre comunidad
    p4 = doc.add_paragraph()
    p4.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r4 = p4.add_run(study_data.get("nombre_comunidad", "").upper())
    r4.bold = True
    r4.font.size = Pt(20)
    r4.font.color.rgb = COLOR_AZUL
    r4.font.name = "Calibri"

    # Pueblo indígena
    if study_data.get("pueblo_indigena"):
        p5 = doc.add_paragraph()
        p5.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r5 = p5.add_run(f"Pueblo {study_data['pueblo_indigena']}")
        r5.font.size = Pt(14)
        r5.font.color.rgb = COLOR_DORADO
        r5.font.name = "Calibri"

    doc.add_paragraph()
    _add_horizontal_rule(doc, COLOR_DORADO)
    doc.add_paragraph()

    # Datos básicos en portada
    info_lines = [
        ("Municipio", study_data.get("municipio", "")),
        ("Departamento", study_data.get("departamento", "")),
        ("Contrato", study_data.get("contrato_referencia", "")),
        ("Elaborado por", "Simonky S.A.S."),
        ("Fecha", date.today().strftime("%d de %B de %Y")),
    ]
    for label, value in info_lines:
        if value:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(f"{label}: {value}")
            r.font.size = Pt(11)
            r.font.color.rgb = COLOR_NEGRO
            r.font.name = "Calibri"

    _page_break(doc)


# ── Sección I — Información general ──────────────────────────────────────────

def _flat_val(v):
    """Para campos del consolidado del tipo {valor, fuente, ...}, devuelve solo el valor."""
    if isinstance(v, dict) and "valor" in v:
        return v["valor"]
    return v


def _add_info_general(
    doc: Document,
    study_data: dict,
    extracciones: list[dict],
    consolidated: dict | None = None,
) -> None:
    _heading1(doc, "III. Información General de la Comunidad")

    ident = (consolidated or {}).get("identificacion") or {}

    _info_table(doc, [
        ("Nombre de la comunidad", _flat_val(ident.get("nombre_comunidad")) or study_data.get("nombre_comunidad", "")),
        ("Autodenominación",       _flat_val(ident.get("autodenominacion")) or ""),
        ("Pueblo indígena",        study_data.get("pueblo_indigena", "")),
        ("Municipio",              _flat_val(ident.get("municipio")) or study_data.get("municipio", "")),
        ("Departamento",           _flat_val(ident.get("departamento")) or study_data.get("departamento", "")),
        ("Vereda",                 _flat_val(ident.get("vereda")) or study_data.get("vereda", "")),
        ("NIT",                    _flat_val(ident.get("nit")) or study_data.get("nit_comunidad", "")),
        ("Contrato referencia",    study_data.get("contrato_referencia", "")),
    ])

    doc.add_paragraph()

    _heading2(doc, "Datos Poblacionales del Corpus")

    pob = (consolidated or {}).get("poblacion") or {}

    if pob.get("personas") or pob.get("familias"):
        # ── Pipeline v2: consolidado ──
        rows: list[tuple[str, str]] = []
        if pob.get("personas"):
            p = pob["personas"] if isinstance(pob["personas"], dict) else {"valor": pob["personas"], "fuente": "—"}
            rows.append(("Personas registradas", f"{p.get('valor', '—')} (según {p.get('fuente', '—')})"))
        if pob.get("familias"):
            f = pob["familias"] if isinstance(pob["familias"], dict) else {"valor": pob["familias"], "fuente": "—"}
            rows.append(("Familias registradas", f"{f.get('valor', '—')} (según {f.get('fuente', '—')})"))
        if pob.get("fecha_censo"):
            fc = pob["fecha_censo"] if isinstance(pob["fecha_censo"], dict) else {"valor": pob["fecha_censo"]}
            rows.append(("Fecha del censo", str(fc.get("valor", "—"))))
        if pob.get("fuente_censo"):
            sc = pob["fuente_censo"] if isinstance(pob["fuente_censo"], dict) else {"valor": pob["fuente_censo"]}
            rows.append(("Fuente del censo", str(sc.get("valor", "—"))))
        if rows:
            _info_table(doc, rows)

        if pob.get("discrepancias"):
            _heading3(doc, "⚠ Discrepancias detectadas")
            for d in pob["discrepancias"][:5]:
                _body(doc,
                    f"En el campo '{d.get('campo', '?')}', {d.get('fuente_a', '?')} reporta "
                    f"{d.get('valor_a', '?')} mientras que {d.get('fuente_b', '?')} reporta "
                    f"{d.get('valor_b', '?')}. Se priorizó el primero.",
                    italic=True,
                )

        if pob.get("distribucion_por_edad"):
            _heading3(doc, "Distribución por edad")
            edad_rows = [(f"Rango {ed.get('rango', '?')}", str(ed.get("cantidad", 0)))
                         for ed in pob["distribucion_por_edad"]]
            if edad_rows:
                _info_table(doc, edad_rows)
    else:
        # ── Pipeline viejo: extracciones planas ──
        pob_tipos = [e for e in extracciones if e.get("tipo_dato") in (
            "familias_count", "personas_count", "fecha_censo", "fuente_censo", "poblacion"
        )]
        if pob_tipos:
            datos_pob = {e["tipo_dato"]: e.get("valor", "") for e in pob_tipos}
            pob_rows = []
            if datos_pob.get("familias_count"):
                pob_rows.append(("Familias registradas", datos_pob["familias_count"]))
            if datos_pob.get("personas_count"):
                pob_rows.append(("Personas registradas", datos_pob["personas_count"]))
            if datos_pob.get("poblacion") and not datos_pob.get("personas_count"):
                pob_rows.append(("Población registrada", datos_pob["poblacion"]))
            if datos_pob.get("fecha_censo"):
                pob_rows.append(("Fecha del censo", datos_pob["fecha_censo"]))
            if datos_pob.get("fuente_censo"):
                pob_rows.append(("Fuente del censo", datos_pob["fuente_censo"]))
            if pob_rows:
                _info_table(doc, pob_rows)
        else:
            _body(doc,
                "Los datos poblacionales se encuentran en el corpus documental adjunto. "
                "Ejecute la extracción documental para poblar esta sección.",
                italic=True,
            )

    notas = study_data.get("notas_adicionales")
    if notas:
        _heading2(doc, "Observaciones Generales")
        _body(doc, notas)


# ── Sección II — Marco legal ──────────────────────────────────────────────────

_MARCO_LEGAL = (
    "El presente estudio se fundamenta en el marco normativo colombiano para el "
    "reconocimiento de comunidades indígenas, en particular: la Constitución Política "
    "de Colombia de 1991 (artículos 7, 8, 63 y 330), el Convenio 169 de la OIT "
    "ratificado mediante la Ley 21 de 1991, el Decreto 2164 de 1995 sobre resguardos "
    "indígenas, la Ley 1152 de 2007 y el Decreto 1071 de 2015 en lo relativo a la "
    "acreditación de comunidades ante el Ministerio del Interior."
)


def _add_marco_legal(doc: Document) -> None:
    _heading1(doc, "II. Marco Legal y Normativo")

    _body(doc, _MARCO_LEGAL)
    _heading2(doc, "Motivos de Reconocimiento")
    motivos = [
        "1. Conservación de la identidad cultural y prácticas ancestrales del pueblo.",
        "2. Existencia de territorio colectivo o área de asentamiento histórico.",
        "3. Estructura organizativa propia con autoridades tradicionales elegidas.",
    ]
    for m in motivos:
        p = doc.add_paragraph(m, style="List Bullet")
        p.paragraph_format.space_after = Pt(3)
        p.runs[0].font.size = Pt(11)
        p.runs[0].font.name = "Calibri"


# ── Sección III — Análisis SIG ────────────────────────────────────────────────

def _add_analisis_sig(
    doc: Document,
    gis_results: list[dict],
    mapa_general_png: bytes | None,
    mapas_por_capa_png: dict[str, bytes] | None,
    buffer_metros: int,
) -> None:
    _heading1(doc, "VIII. Análisis Georreferenciado del Territorio")

    _body(
        doc,
        f"Se realizó un análisis espacial de las cuatro capas temáticas principales "
        f"(Prácticas Culturales, Expresiones Simbólicas, Entornos Territoriales y "
        f"Procesos Organizativos) aplicando buffers de {buffer_metros} metros, "
        f"matrices de distancia entre pares de capas y análisis de solapamiento "
        f"espacial. El sistema de referencia de cálculo utilizado es "
        f"MAGNA-SIRGAS (EPSG:3116).",
    )

    # Mapa general
    if mapa_general_png:
        _heading2(doc, "Mapa General de Distribución Territorial")
        doc.add_paragraph()
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        run.add_picture(io.BytesIO(mapa_general_png), width=Cm(16))
        cap = doc.add_paragraph("Figura 1. Distribución espacial de los sitios registrados.")
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.runs[0].font.size = Pt(9)
        cap.runs[0].font.color.rgb = COLOR_GRIS
        cap.runs[0].italic = True

    # Matrices de distancia
    matrices = [r for r in gis_results if r.get("tipo_resultado") == "matriz_distancia"]
    if matrices:
        _heading2(doc, "Matrices de Distancia entre Capas")
        headers = ["Capa A", "Capa B", "N puntos A", "N puntos B",
                   "Dist. mín. (m)", "Dist. media (m)", "Dist. máx. (m)"]
        data = []
        for m in matrices:
            r = m.get("resultado_json", {})
            capas = r.get("capas", ["—", "—"])
            data.append([
                capas[0].replace("_PUNT", ""),
                capas[1].replace("_PUNT", ""),
                str(r.get("n_puntos_a", "—")),
                str(r.get("n_puntos_b", "—")),
                str(r.get("distancia_min_m", "—")),
                str(r.get("distancia_media_m", "—")),
                str(r.get("distancia_max_m", "—")),
            ])
        _matrix_table(doc, headers, data)
        doc.add_paragraph()

    # Solapamientos
    overlaps = [r for r in gis_results if r.get("tipo_resultado") == "solapamiento"]
    if overlaps:
        _heading2(doc, "Análisis de Solapamiento Espacial")
        headers = ["Capa A", "Capa B", "Área buffer A (m²)",
                   "Área buffer B (m²)", "Intersección (m²)", "% Intersección A", "Solapamiento"]
        data = []
        for o in overlaps:
            r = o.get("resultado_json", {})
            capas = r.get("capas", ["—", "—"])
            data.append([
                capas[0].replace("_PUNT", ""),
                capas[1].replace("_PUNT", ""),
                str(r.get("area_buffer_a_m2", "—")),
                str(r.get("area_buffer_b_m2", "—")),
                str(r.get("area_interseccion_m2", "—")),
                f"{r.get('porcentaje_interseccion_a', 0)}%",
                "Sí" if r.get("hay_solapamiento") else "No",
            ])
        _matrix_table(doc, headers, data)
        doc.add_paragraph()

    # Mapas por capa
    if mapas_por_capa_png:
        _heading2(doc, "Mapas Temáticos por Capa")
        nombres = {
            "Practicas_Culturales_PUNT":   "Prácticas Culturales",
            "Expresiones_Simbolicas_PUNT": "Expresiones Simbólicas",
            "Entornos_Territoriales_PUNT": "Entornos Territoriales",
            "Procesos_Organizativos_PUNT": "Procesos Organizativos",
        }
        for i, (nombre_capa, png) in enumerate(mapas_por_capa_png.items(), start=2):
            _heading3(doc, nombres.get(nombre_capa, nombre_capa))
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run()
            run.add_picture(io.BytesIO(png), width=Cm(14))
            cap = doc.add_paragraph(
                f"Figura {i}. Distribución de {nombres.get(nombre_capa, nombre_capa)}."
            )
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cap.runs[0].font.size = Pt(9)
            cap.runs[0].font.color.rgb = COLOR_GRIS
            cap.runs[0].italic = True


# ── Sección I — Presentación ──────────────────────────────────────────────────

def _add_presentacion(doc: Document, study_data: dict, ai_content: dict) -> None:
    _heading1(doc, "I. Presentación")
    texto_ia = ai_content.get("presentacion")
    if texto_ia:
        for parrafo in texto_ia.split("\n\n"):
            parrafo = parrafo.strip()
            if parrafo:
                _body(doc, parrafo)
    else:
        comunidad = study_data.get("nombre_comunidad", "la comunidad")
        contrato  = study_data.get("contrato_referencia", "")
        municipio = study_data.get("municipio", "")
        pueblo    = study_data.get("pueblo_indigena", "")
        _body(doc,
            f"El presente documento constituye el estudio etnológico elaborado en el marco del "
            f"{'contrato ' + contrato if contrato else 'contrato suscrito'} con el Ministerio del "
            f"Interior — Dirección de Asuntos Indígenas, ROM y Minorías (DAIRM), con el propósito "
            f"de adelantar el proceso de reconocimiento formal de {comunidad}"
            + (f", comunidad perteneciente al pueblo {pueblo}" if pueblo else "")
            + (f", ubicada en el municipio de {municipio}" if municipio else "")
            + "."
        )
        _body(doc,
            "La investigación se desarrolló mediante la revisión y análisis del corpus documental "
            "allegado por la comunidad, que incluye actas de constitución, censos, declaraciones "
            "de identidad, registros culturales y demás documentación soporte. La información "
            "recogida fue sistematizada y contrastada con la normativa vigente para el "
            "reconocimiento de comunidades indígenas en Colombia.",
            italic=True,
        )


# ── Sección IV — Reseña histórica ────────────────────────────────────────────

def _add_resena_historica(doc: Document, ai_content: dict, extracciones: list[dict]) -> None:
    _heading1(doc, "IV. Reseña Histórica")
    texto = ai_content.get("resena_historica")
    if texto:
        for parrafo in texto.split("\n\n"):
            parrafo = parrafo.strip()
            if parrafo:
                _body(doc, parrafo)
    else:
        _fallback_por_tipos(doc, extracciones,
            ["narrativa_origen", "trayectoria_migratoria", "fecha_historica", "evento_historico"],
            "Los antecedentes históricos, el proceso de asentamiento y los motivos del "
            "reconocimiento se encuentran documentados en el corpus adjunto, en particular "
            "en la reseña histórica y las actas de constitución.",
        )


# ── Sección V — Conciencia de identidad ──────────────────────────────────────

def _add_conciencia_identidad(doc: Document, ai_content: dict, extracciones: list[dict]) -> None:
    _heading1(doc, "V. Conciencia de Identidad")
    texto = ai_content.get("conciencia_identidad")
    if texto:
        for parrafo in texto.split("\n\n"):
            parrafo = parrafo.strip()
            if parrafo:
                _body(doc, parrafo)
    else:
        _fallback_por_tipos(doc, extracciones,
            ["autoidentificacion", "nombre_indigena", "clan_indigena", "lengua_indigena", "nivel_uso_lengua"],
            "Los elementos de auto-identificación, uso de la lengua y continuidad cultural "
            "se encuentran registrados en las declaraciones y documentos del corpus adjunto.",
        )


# ── Sección VI — Caracterización etnológica ──────────────────────────────────

def _add_caracterizacion(doc: Document, extracciones: list[dict], ai_content: dict) -> None:
    _heading1(doc, "VI. Caracterización Etnológica")
    _body(doc,
        "A continuación se presenta la caracterización etnológica de la comunidad, "
        "organizada en dos dimensiones: la intrarelacional, que abarca los elementos "
        "culturales, espirituales y organizativos propios; y la interrelacional, que "
        "describe las relaciones con el entorno institucional y social externo.",
    )

    # 6.1 Intrarelacional
    _heading2(doc, "6.1 Caracterización Intrarelacional")
    texto_intra = ai_content.get("caracterizacion_intrarelacional")
    if texto_intra:
        for parrafo in texto_intra.split("\n\n"):
            parrafo = parrafo.strip()
            if parrafo:
                _body(doc, parrafo)
    else:
        _fallback_por_tipos(doc, extracciones,
            [
                "actividad_cultural", "ritual_central", "cosmogonia", "lugar_sagrado",
                "planta_sagrada", "tecnologia_espiritual", "elemento_sagrado",
                "actividad_subsistencia", "herramienta_tradicional",
                "estructura_politica", "autoridad_cargo", "reglamento_interno_detalle",
                "territorio_descripcion", "vereda", "resguardo",
            ],
            "El análisis de las prácticas culturales, rituales, territorialidad y gobierno "
            "propio reposa en el corpus documental anexo.",
        )

    # 6.2 Interrelacional
    _heading2(doc, "6.2 Caracterización Interrelacional")
    texto_inter = ai_content.get("caracterizacion_interrelacional")
    if texto_inter:
        for parrafo in texto_inter.split("\n\n"):
            parrafo = parrafo.strip()
            if parrafo:
                _body(doc, parrafo)
    else:
        _fallback_por_tipos(doc, extracciones,
            ["alianza_interetnica", "relacion_institucional", "actores_externos"],
            "Las relaciones interinstitucionales y con comunidades vecinas están "
            "documentadas en el corpus adjunto.",
        )


# ── Sección VII — Prospectiva ─────────────────────────────────────────────────

def _add_prospectiva(doc: Document, ai_content: dict, extracciones: list[dict]) -> None:
    _heading1(doc, "VII. Prospectiva")
    texto = ai_content.get("prospectiva")
    if texto:
        for parrafo in texto.split("\n\n"):
            parrafo = parrafo.strip()
            if parrafo:
                _body(doc, parrafo)
    else:
        _fallback_por_tipos(doc, extracciones,
            ["amenaza_seguridad", "despojo_historico", "vision_futuro", "actividad_economica"],
            "Las amenazas al territorio, los despojos históricos y la visión de futuro de "
            "la comunidad están registrados en el corpus documental adjunto.",
        )


# ── Sección IX — Conclusiones ─────────────────────────────────────────────────

def _add_conclusiones(doc: Document, study_data: dict, n_capas: int, n_puntos: int, ai_content: dict) -> None:
    _heading1(doc, "IX. Conclusiones y Recomendaciones")

    texto_ia = ai_content.get("conclusiones")
    if texto_ia:
        for parrafo in texto_ia.split("\n\n"):
            parrafo = parrafo.strip()
            if parrafo:
                _body(doc, parrafo)
    else:
        comunidad = study_data.get("nombre_comunidad", "la comunidad")
        pueblo = study_data.get("pueblo_indigena", "")
        municipio = study_data.get("municipio", "")
        dept = study_data.get("departamento", "")

        texto = (
            f"El análisis etnológico realizado sobre {comunidad}"
            + (f", perteneciente al pueblo {pueblo}," if pueblo else "")
            + f" ubicada en el municipio de {municipio}, departamento de {dept}, "
            f"permitió identificar y documentar los elementos constitutivos de su identidad "
            f"cultural. El corpus documental analizado y los datos georreferenciados "
            f"({n_capas} capas, {n_puntos} sitios) respaldan la continuidad cultural y la "
            f"organización propia de la comunidad. Con base en la evidencia recopilada, "
            f"se recomienda continuar con el proceso de reconocimiento formal ante la DAIRM."
        )
        _body(doc, texto)

        _heading2(doc, "Recomendaciones")
        recomendaciones = [
            "Verificar y actualizar los datos del autocenso con las autoridades tradicionales.",
            "Complementar el registro fotográfico y etnográfico de los sitios de valor cultural.",
            "Coordinar con la Dirección de Asuntos Indígenas la agenda de visita de verificación.",
            "Mantener actualizados los registros SIG a medida que se identifiquen nuevos sitios.",
            "Consolidar el reglamento interno y el plan de vida de la comunidad.",
        ]
        for r in recomendaciones:
            p = doc.add_paragraph(r, style="List Bullet")
            p.runs[0].font.size = Pt(11)
            p.runs[0].font.name = "Calibri"


# ── Sección X — Fuentes citadas (Sprint Drive E) ──────────────────────────────

_ROL_LABEL: dict[str, str] = {
    "ficha_precampo": "Ficha de Pre-campo",
    "reglamento": "Reglamento Interno",
    "acta_eleccion": "Acta de Elección",
    "acta_posesion": "Acta de Posesión",
    "autocenso": "Autocenso",
    "autocenso_depurado": "Autocenso Depurado",
    "censo_comunidad": "Censo de la Comunidad",
    "resena_historica": "Reseña Histórica",
    "ficha_comision": "Ficha de Comisión",
    "diario_campo": "Diario de Campo",
    "acta_inicio": "Acta de Inicio",
    "arbol_riesgo": "Árbol de Riesgos",
    "registro_asistencia": "Registro de Asistencia",
    "apuntes_reuniones": "Apuntes de Reuniones",
    "cartografia_social": "Cartografía Social",
    "geopackage": "GeoPackage / Shapefile",
    "proyecto_qgis": "Proyecto QGIS",
    "evidencia_foto": "Evidencia Fotográfica",
    "solicitud_formal": "Solicitud Formal",
    "rut_comunidad": "RUT de la Comunidad",
    "mapa_territorial": "Mapa Territorial",
    "base_datos_dane": "Base de Datos DANE",
    "cronograma": "Cronograma",
    "generico": "Documento sin tipo definido",
    "otro": "Otro",
}


def _add_fuentes_citadas(doc: Document, consolidated: dict | None) -> None:
    """Sección X del informe: archivos del corpus que aportaron datos al estudio."""
    if not consolidated:
        return
    fuentes = consolidated.get("fuentes") or []
    con_datos = [f for f in fuentes if f.get("tiene_datos")]
    if not con_datos:
        return

    _heading1(doc, "X. Fuentes Citadas y Corpus Documental")
    _body(doc,
        "A continuación se relacionan los documentos del corpus que aportaron datos al "
        "análisis etnológico de esta comunidad. Cada uno fue clasificado por tipo, "
        "procesado mediante extracción dirigida y consolidado en una base de datos "
        "estructurada que sustenta las secciones anteriores del informe."
    )

    # Tabla con columnas: archivo, tipo, método, fecha de procesamiento
    headers = ["Archivo", "Tipo de documento", "Método", "Procesado"]
    data = []
    for f in con_datos:
        rol = f.get("rol") or "otro"
        nombre = f.get("nombre_archivo") or "—"
        if len(nombre) > 60:
            nombre = nombre[:57] + "…"
        metodo = f.get("fuente_extraccion") or f.get("extraido_con_modelo") or "—"
        fecha = (f.get("extraido_en") or "")[:10] or "—"
        data.append([nombre, _ROL_LABEL.get(rol, rol), metodo, fecha])
    _matrix_table(doc, headers, data)

    # Si hubo archivos del corpus sin datos, registrarlos
    sin_datos = [f for f in fuentes if not f.get("tiene_datos")]
    if sin_datos:
        doc.add_paragraph()
        _heading2(doc, "Archivos del corpus no procesados")
        _body(doc,
            f"Los siguientes {len(sin_datos)} archivos forman parte del corpus pero "
            "aún no produjeron datos estructurados (procesamiento pendiente, formato "
            "no soportado o errores que requieren atención):",
            italic=True,
        )
        data_sd = []
        for f in sin_datos:
            nombre = (f.get("nombre_archivo") or "—")[:60]
            rol = _ROL_LABEL.get(f.get("rol") or "otro", "Otro")
            data_sd.append([nombre, rol, f.get("fuente_extraccion") or "—"])
        if data_sd:
            _matrix_table(doc, ["Archivo", "Tipo", "Método/estado"], data_sd)


# ── Helper interno: fallback con datos del corpus ─────────────────────────────

def _fallback_por_tipos(
    doc: Document,
    extracciones: list[dict],
    tipos: list[str],
    nota_fallback: str,
) -> None:
    """Muestra los valores extraídos de los tipos indicados; si no hay, pone la nota."""
    relevantes = [
        e for e in extracciones
        if e.get("tipo_dato") in tipos and (e.get("valor") or "").strip()
    ]
    if relevantes:
        vistos: set[str] = set()
        for e in relevantes:
            valor = (e.get("valor") or "").strip()
            if valor and valor not in vistos and len(valor) > 5:
                vistos.add(valor)
                p = doc.add_paragraph(style="List Bullet")
                p.paragraph_format.space_after = Pt(3)
                run = p.add_run(valor)
                run.font.size = Pt(11)
                run.font.name = "Calibri"
    _body(doc, nota_fallback, italic=True)


# ── Constructor principal ──────────────────────────────────────────────────────

def build_report(
    study_data: dict,
    extracciones: list[dict],
    gis_results: list[dict],
    mapa_general_png: bytes | None = None,
    mapas_por_capa_png: dict[str, bytes] | None = None,
    ai_content: dict | None = None,
    consolidated_data: dict | None = None,
) -> bytes:
    """
    Construye el documento Word completo y retorna los bytes del .docx.

    Args:
        study_data:       Dict con los campos del modelo Study.
        extracciones:     Lista de CorpusExtraction como dicts (pipeline viejo).
        gis_results:      Lista de GISResult como dicts (con resultado_json).
        mapa_general_png: PNG del mapa general (opcional).
        mapas_por_capa_png: Dict {nombre_capa: bytes PNG} (opcional).
        ai_content:       Texto narrativo por sección (de ai_writer).
        consolidated_data: Sprint Drive E — consolidado del estudio. Si está
                          presente, las tablas y la sección de fuentes citadas
                          se llenan desde aquí en lugar de las extracciones.
    """
    doc = Document()

    # Márgenes
    for section in doc.sections:
        section.top_margin    = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin   = Cm(3.0)
        section.right_margin  = Cm(2.5)

    # Encabezado de página
    header = doc.sections[0].header
    h_para = header.paragraphs[0]
    h_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    h_run = h_para.add_run("EtnoSIG — Simonky S.A.S.")
    h_run.font.size = Pt(8)
    h_run.font.color.rgb = COLOR_GRIS
    h_run.font.name = "Calibri"

    # Pie de página con número
    footer = doc.sections[0].footer
    f_para = footer.paragraphs[0]
    f_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    f_run = f_para.add_run("Página ")
    f_run.font.size = Pt(8)
    f_run.font.color.rgb = COLOR_GRIS
    pgNum = OxmlElement("w:fldChar")
    pgNum.set(qn("w:fldCharType"), "begin")
    f_run._r.append(pgNum)
    ins = OxmlElement("w:instrText")
    ins.text = " PAGE "
    f_run._r.append(ins)
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    f_run._r.append(end)

    ai = ai_content or {}

    # Calcular métricas SIG
    n_capas = len(mapas_por_capa_png) if mapas_por_capa_png else 0
    n_puntos = sum(
        r.get("resultado_json", {}).get("n_puntos_a", 0)
        for r in gis_results
        if r.get("tipo_resultado") == "matriz_distancia"
    )

    # Secciones del informe — estructura real FASE 3
    _add_portada(doc, study_data)
    _add_presentacion(doc, study_data, ai)
    _page_break(doc)
    _add_marco_legal(doc)
    _page_break(doc)
    _add_info_general(doc, study_data, extracciones, consolidated_data)
    _page_break(doc)
    _add_resena_historica(doc, ai, extracciones)
    _page_break(doc)
    _add_conciencia_identidad(doc, ai, extracciones)
    _page_break(doc)
    _add_caracterizacion(doc, extracciones, ai)
    _page_break(doc)
    _add_prospectiva(doc, ai, extracciones)
    _page_break(doc)
    _add_analisis_sig(
        doc, gis_results, mapa_general_png, mapas_por_capa_png,
        study_data.get("buffer_metros", 50),
    )
    _page_break(doc)
    _add_conclusiones(doc, study_data, n_capas, n_puntos, ai)

    # Sprint Drive E — sección X: fuentes citadas
    if consolidated_data:
        _page_break(doc)
        _add_fuentes_citadas(doc, consolidated_data)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


def docx_to_pdf(docx_bytes: bytes) -> bytes:
    """
    Convierte bytes de un .docx a PDF usando LibreOffice headless.
    Lanza RuntimeError si LibreOffice no está instalado o la conversión falla.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        docx_path = Path(tmpdir) / "report.docx"
        docx_path.write_bytes(docx_bytes)

        result = subprocess.run(
            [
                "libreoffice", "--headless", "--norestore",
                "--convert-to", "pdf",
                "--outdir", tmpdir,
                str(docx_path),
            ],
            capture_output=True,
            timeout=120,
        )

        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace")
            raise RuntimeError(f"LibreOffice conversion failed: {stderr}")

        pdf_path = Path(tmpdir) / "report.pdf"
        if not pdf_path.exists():
            raise RuntimeError("LibreOffice no produjo el archivo PDF")

        return pdf_path.read_bytes()
