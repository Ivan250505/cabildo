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
from datetime import date, datetime
from pathlib import Path

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

def _add_info_general(doc: Document, study_data: dict, extracciones: list[dict]) -> None:
    _heading1(doc, "I. Información General de la Comunidad")

    _info_table(doc, [
        ("Nombre de la comunidad", study_data.get("nombre_comunidad", "")),
        ("Pueblo indígena",        study_data.get("pueblo_indigena", "")),
        ("Municipio",              study_data.get("municipio", "")),
        ("Departamento",           study_data.get("departamento", "")),
        ("Vereda",                 study_data.get("vereda", "")),
        ("NIT",                    study_data.get("nit_comunidad", "")),
        ("Contrato referencia",    study_data.get("contrato_referencia", "")),
    ])

    doc.add_paragraph()

    # Extracciones NLP relevantes
    pob = [e for e in extracciones if e.get("tipo_dato") == "poblacion"]
    if pob:
        _heading2(doc, "Datos Poblacionales Identificados")
        for e in pob[:5]:
            _label_value(doc, "Población registrada", e.get("valor", ""))

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
    _heading1(doc, "III. Análisis Georreferenciado del Territorio")

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


# ── Sección IV — Historia y contexto ─────────────────────────────────────────

def _add_historia(doc: Document, ai_content: dict) -> None:
    _heading1(doc, "III. Historia y Contexto de la Comunidad")
    texto = ai_content.get("historia")
    if texto:
        for parrafo in texto.split("\n\n"):
            parrafo = parrafo.strip()
            if parrafo:
                _body(doc, parrafo)
    else:
        _body(
            doc,
            "La historia de la comunidad, su origen y los antecedentes del proceso "
            "de reconocimiento ante el Ministerio del Interior reposan en el corpus "
            "documental anexo, en particular en la reseña histórica y las actas de "
            "elección de autoridades tradicionales.",
            italic=True,
        )


# ── Sección V — Caracterización etnológica ────────────────────────────────────

def _add_caracterizacion(doc: Document, extracciones: list[dict], ai_content: dict) -> None:
    _heading1(doc, "IV. Caracterización Etnológica")

    _body(
        doc,
        "A continuación se presentan los elementos de identidad cultural identificados "
        "durante el trabajo de campo y en el análisis del corpus documental, "
        "organizados según las cuatro dimensiones temáticas de la investigación.",
    )

    subsecciones = [
        ("Prácticas Culturales", "practicas_culturales"),
        ("Expresiones Simbólicas", "expresiones_simbolicas"),
        ("Entornos Territoriales", "entornos_territoriales"),
        ("Procesos Organizativos", "procesos_organizativos"),
    ]

    for titulo, ai_key in subsecciones:
        _heading2(doc, titulo)
        texto_ia = ai_content.get(ai_key)
        if texto_ia:
            for parrafo in texto_ia.split("\n\n"):
                parrafo = parrafo.strip()
                if parrafo:
                    _body(doc, parrafo)
        else:
            # Fallback: filtrar extracciones por palabras clave
            palabras = {
                "practicas_culturales": ["practica", "cultural", "tradicion", "actividad_cultural"],
                "expresiones_simbolicas": ["simbolo", "expresion", "ritual", "ceremonia"],
                "entornos_territoriales": ["territorio", "entorno", "sitio", "lugar"],
                "procesos_organizativos": ["organizacion", "autoridad", "gobernanza", "representante"],
            }
            claves = palabras.get(ai_key, [])
            relevantes = [
                e for e in extracciones
                if any(k in (e.get("tipo_dato", "") + " " + (e.get("valor") or "")).lower()
                       for k in claves)
            ]
            if relevantes:
                for e in relevantes[:8]:
                    valor = e.get("valor", "").strip()
                    if valor:
                        p = doc.add_paragraph(f"• {valor}", style="List Bullet")
                        p.runs[0].font.size = Pt(11)
                        p.runs[0].font.name = "Calibri"
            else:
                _body(
                    doc,
                    "Información recopilada durante el trabajo de campo. Ver corpus documental anexo.",
                    italic=True,
                )


# ── Sección VI — Conclusiones ─────────────────────────────────────────────────

def _add_conclusiones(doc: Document, study_data: dict, n_capas: int, n_puntos: int, ai_content: dict) -> None:
    _heading1(doc, "V. Conclusiones y Recomendaciones")

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
            f"El análisis etnológico realizado a {comunidad}"
            + (f", perteneciente al pueblo {pueblo}," if pueblo else "")
            + f" ubicada en el municipio de {municipio}, departamento de {dept}, "
            f"permitió identificar y documentar los elementos constitutivos de su identidad "
            f"cultural a través del análisis de {n_capas} capas temáticas con un total de "
            f"{n_puntos} sitios georreferenciados. "
            f"Con base en la evidencia documental y geográfica recopilada, se recomienda "
            f"continuar con el proceso de reconocimiento ante el Ministerio del Interior."
        )
        _body(doc, texto)

        _heading2(doc, "Recomendaciones")
        recomendaciones = [
            "Verificar y actualizar los datos del autocenso con las autoridades tradicionales.",
            "Complementar el registro fotográfico de los sitios de valor cultural identificados.",
            "Coordinar con la Dirección de Asuntos Indígenas la agenda de visita oficial.",
            "Mantener actualizados los registros SIG a medida que se identifiquen nuevos sitios.",
        ]
        for r in recomendaciones:
            p = doc.add_paragraph(r, style="List Bullet")
            p.runs[0].font.size = Pt(11)
            p.runs[0].font.name = "Calibri"


# ── Constructor principal ──────────────────────────────────────────────────────

def build_report(
    study_data: dict,
    extracciones: list[dict],
    gis_results: list[dict],
    mapa_general_png: bytes | None = None,
    mapas_por_capa_png: dict[str, bytes] | None = None,
    ai_content: dict | None = None,
) -> bytes:
    """
    Construye el documento Word completo y retorna los bytes del .docx.

    Args:
        study_data:       Dict con los campos del modelo Study.
        extracciones:     Lista de CorpusExtraction como dicts.
        gis_results:      Lista de GISResult como dicts (con resultado_json).
        mapa_general_png: PNG del mapa general (opcional).
        mapas_por_capa_png: Dict {nombre_capa: bytes PNG} (opcional).
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

    # Secciones del informe
    _add_portada(doc, study_data)
    _add_marco_legal(doc)
    _page_break(doc)
    _add_info_general(doc, study_data, extracciones)
    _page_break(doc)
    _add_historia(doc, ai)
    _page_break(doc)
    _add_caracterizacion(doc, extracciones, ai)
    _page_break(doc)

    # Calcular métricas SIG para conclusiones
    n_capas = len(mapas_por_capa_png) if mapas_por_capa_png else 0
    n_puntos = sum(
        r.get("resultado_json", {}).get("n_puntos_a", 0)
        for r in gis_results
        if r.get("tipo_resultado") == "matriz_distancia"
    )

    _add_analisis_sig(
        doc, gis_results, mapa_general_png, mapas_por_capa_png,
        study_data.get("buffer_metros", 50),
    )
    _page_break(doc)
    _add_conclusiones(doc, study_data, n_capas, n_puntos, ai)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()
