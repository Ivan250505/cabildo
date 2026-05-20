"""
PDF página por página con OCR selectivo (Sprint Drive D).

A diferencia del extractor.py viejo (que decidía OCR "todo o nada" sobre el
PDF completo), este módulo:
  - Lee cada página con pdfplumber.
  - Detecta cuáles tienen texto extraíble y cuáles no.
  - Solo las páginas sin texto pasan por OCR (Tesseract o Gemini Vision por imagen).
  - Concatena todo con marcadores de fuente por página.

Beneficio: un PDF de 138 páginas con 4 escaneadas paga OCR de 4 páginas,
no del documento entero.
"""
from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)


# Mínimo de chars para considerar que una página tiene texto nativo extraíble
_MIN_CHARS_PER_PAGE = 30


# ── Análisis página por página ────────────────────────────────────────────────

def analyze_pdf_pages(path: str | Path) -> dict:
    """
    Recorre el PDF y clasifica cada página como 'texto' o 'sin_texto'.

    Returns:
        {
            "total_paginas": int,
            "paginas": [{"num": 1, "chars": 1234, "fuente": "texto"}, ...],
            "paginas_sin_texto": [3, 5, 17],
            "ratio_con_texto": float (0..1),
        }
    """
    import pdfplumber

    out_paginas: list[dict] = []
    sin_texto: list[int] = []
    try:
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                try:
                    t = page.extract_text() or ""
                except Exception as e:
                    logger.debug("Página %d sin texto extraíble: %s", i, e)
                    t = ""
                chars = len(t.strip())
                fuente = "texto" if chars >= _MIN_CHARS_PER_PAGE else "sin_texto"
                if fuente == "sin_texto":
                    sin_texto.append(i)
                out_paginas.append({"num": i, "chars": chars, "fuente": fuente})
    except Exception as e:
        logger.warning("No se pudo analizar el PDF %s: %s", path, e)
        return {"total_paginas": 0, "paginas": [], "paginas_sin_texto": [], "ratio_con_texto": 0.0}

    total = len(out_paginas)
    con_texto = total - len(sin_texto)
    return {
        "total_paginas": total,
        "paginas": out_paginas,
        "paginas_sin_texto": sin_texto,
        "ratio_con_texto": (con_texto / total) if total else 0.0,
    }


# ── OCR de una sola página vía Gemini Vision ──────────────────────────────────

def _ocr_page_via_vision(
    pdf_path: str | Path,
    page_num: int,
    api_key: str,
    model_name: str,
) -> str:
    """
    Renderiza una página específica como imagen y la pasa por Gemini Vision.
    Retorna "" si pdf2image no está disponible o la llamada falla.
    """
    try:
        from pdf2image import convert_from_path
    except ImportError:
        logger.info("pdf2image no instalado — no se puede OCR por página vía Vision")
        return ""

    try:
        images = convert_from_path(str(pdf_path), dpi=200, first_page=page_num, last_page=page_num)
    except Exception as e:
        logger.warning("pdf2image falló para %s pág %d: %s", pdf_path, page_num, e)
        return ""

    if not images:
        return ""

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        logger.info("google-genai no instalado — no se puede Vision por página")
        return ""

    img = images[0]
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    raw_bytes = buf.getvalue()

    client = genai.Client(api_key=api_key)
    prompt = (
        f"Transcribe TODO el texto visible en esta página (página {page_num}) "
        "de un documento etnológico colombiano. Si hay tablas, extrae los valores. "
        "Responde solo el texto transcrito, sin comentarios."
    )

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=[
                types.Part.from_bytes(data=raw_bytes, mime_type="image/png"),
                prompt,
            ],
        )
        text = (response.text or "").strip()
        if text:
            logger.info("Vision (página %d) extrajo %d chars de %s", page_num, len(text), Path(pdf_path).name)
        return text
    except Exception as e:
        logger.warning("Gemini Vision falló para %s pág %d: %s", pdf_path, page_num, e)
        return ""


# ── OCR por página con Tesseract ──────────────────────────────────────────────

def _ocr_page_via_tesseract(pdf_path: str | Path, page_num: int) -> str:
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError:
        return ""
    try:
        images = convert_from_path(str(pdf_path), dpi=200, first_page=page_num, last_page=page_num)
    except Exception as e:
        logger.warning("pdf2image (Tesseract) falló para %s pág %d: %s", pdf_path, page_num, e)
        return ""
    if not images:
        return ""
    try:
        text = pytesseract.image_to_string(images[0], lang="spa").strip()
        if text:
            logger.info("Tesseract (página %d) extrajo %d chars de %s", page_num, len(text), Path(pdf_path).name)
        return text
    except pytesseract.TesseractNotFoundError:
        return ""
    except Exception as e:
        logger.warning("Tesseract falló para %s pág %d: %s", pdf_path, page_num, e)
        return ""


# ── Pipeline selectivo ────────────────────────────────────────────────────────

def extract_pdf_text_selective(
    path: str | Path,
    gemini_api_key: str | None = None,
    gemini_model: str = "gemini-2.0-flash-lite",
) -> tuple[str, str, dict]:
    """
    Lee un PDF mezclando extracción local (pdfplumber) en páginas con texto y
    OCR por página solo en las que no lo tienen.

    Returns: (texto_concatenado, metodo_extraccion, meta)
        metodo_extraccion ∈ {"local", "ocr_tesseract_paginas", "ocr_vision_paginas",
                              "mixto", "failed"}
        meta: {"total_paginas", "paginas_ocr", "paginas_local", "engines_usados": [...]}
    """
    import pdfplumber

    analysis = analyze_pdf_pages(path)
    total = analysis["total_paginas"]
    sin_texto = set(analysis["paginas_sin_texto"])

    if total == 0:
        return "", "failed", {"total_paginas": 0, "paginas_ocr": 0, "paginas_local": 0, "engines_usados": []}

    paginas_texto: list[str] = [""] * total
    engines_por_pagina: dict[int, str] = {}

    # Páginas con texto nativo: extraer con pdfplumber
    try:
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                if i in sin_texto:
                    continue
                try:
                    t = page.extract_text() or ""
                except Exception:
                    t = ""
                if t.strip():
                    paginas_texto[i - 1] = t
                    engines_por_pagina[i] = "local"
                else:
                    sin_texto.add(i)
    except Exception as e:
        logger.warning("pdfplumber falló durante extracción selectiva: %s", e)

    # Páginas sin texto: OCR selectivo
    for page_num in sorted(sin_texto):
        text = _ocr_page_via_tesseract(path, page_num)
        engine = "tesseract"
        if not text and gemini_api_key:
            text = _ocr_page_via_vision(path, page_num, gemini_api_key, gemini_model)
            engine = "vision"
        if text:
            paginas_texto[page_num - 1] = f"[página {page_num} — OCR {engine}]\n{text}"
            engines_por_pagina[page_num] = engine
        else:
            engines_por_pagina[page_num] = "fallo"

    # Concatenar
    full_text = "\n\n".join(p for p in paginas_texto if p.strip())

    # Resumir método
    engines_usados = sorted(set(engines_por_pagina.values()) - {"fallo"})
    paginas_ocr = sum(1 for e in engines_por_pagina.values() if e in ("tesseract", "vision"))
    paginas_local = sum(1 for e in engines_por_pagina.values() if e == "local")

    if not full_text.strip():
        metodo = "failed"
    elif paginas_ocr == 0:
        metodo = "local"
    elif paginas_local == 0:
        if "vision" in engines_usados:
            metodo = "ocr_vision_paginas"
        else:
            metodo = "ocr_tesseract_paginas"
    else:
        metodo = "mixto"

    return full_text, metodo, {
        "total_paginas": total,
        "paginas_ocr": paginas_ocr,
        "paginas_local": paginas_local,
        "paginas_fallidas": sum(1 for e in engines_por_pagina.values() if e == "fallo"),
        "engines_usados": engines_usados,
    }
