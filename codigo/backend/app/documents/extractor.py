"""
Document extraction pipeline.
Reads PDFs, DOCX, XLSX and image files and extracts structured text
and ethnological entities via spaCy NER. Uses Gemini Vision for
scanned PDFs and images when api_key is provided.
"""
from __future__ import annotations

import base64
import logging
import mimetypes
import re
from pathlib import Path
from typing import Generator

import pdfplumber
import spacy
from docx import Document as DocxDocument

logger = logging.getLogger(__name__)

# Lazy-load the spaCy model to avoid loading it at import time
_nlp: spacy.language.Language | None = None

# Min chars from pdfplumber to consider a PDF as text-based (not scanned)
_MIN_TEXT_CHARS = 150


def _get_nlp(model_name: str = "es_core_news_lg") -> spacy.language.Language:
    global _nlp
    if _nlp is None:
        _nlp = spacy.load(model_name)
    return _nlp


# ── Text extraction ───────────────────────────────────────────────────────────

def extract_text_pdf(path: str | Path) -> str:
    """Extract all text from a PDF using pdfplumber (text-layer only)."""
    texts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                texts.append(t)
    return "\n\n".join(texts)


def extract_text_docx(path: str | Path) -> str:
    doc = DocxDocument(str(path))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_text_excel(path: str | Path) -> str:
    """Extract all cell values from an Excel file (.xlsx / .xls)."""
    import openpyxl
    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    sheets: list[str] = []
    for sheet in wb.worksheets:
        rows: list[str] = []
        for row in sheet.iter_rows(values_only=True):
            cells = [str(v).strip() for v in row if v is not None and str(v).strip()]
            if cells:
                rows.append(" | ".join(cells))
        if rows:
            sheets.append(f"[Hoja: {sheet.title}]\n" + "\n".join(rows))
    wb.close()
    return "\n\n".join(sheets)


def extract_text_via_vision(
    path: str | Path,
    api_key: str,
    model_name: str = "gemini-2.0-flash-lite",
) -> str:
    """
    Use Gemini Vision to extract text from a scanned PDF or image.
    Uses the new google-genai SDK with inline bytes only (no Files API).
    Returns empty string on failure.
    """
    from google import genai
    from google.genai import types

    path = Path(path)
    mime, _ = mimetypes.guess_type(str(path))
    if not mime:
        _mime_map = {
            ".pdf":  "application/pdf",
            ".jpg":  "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png":  "image/png",
            ".heic": "image/heic",
            ".webp": "image/webp",
        }
        mime = _mime_map.get(path.suffix.lower(), "application/octet-stream")

    client = genai.Client(api_key=api_key)

    prompt = (
        "Eres un asistente de extracción de documentos colombianos. "
        "Transcribe TODO el texto visible en este documento o imagen tal como aparece. "
        "Si hay tablas, extrae todos los valores. No agregues comentarios, solo el texto."
    )

    raw_bytes = path.read_bytes()

    # Inline bytes (más confiable que Files API)
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=[
                types.Part.from_bytes(data=raw_bytes, mime_type=mime),
                prompt,
            ],
        )
        text = (response.text or "").strip()
        if text:
            logger.info("Vision (inline) extrajo %d chars de %s", len(text), path.name)
        return text
    except Exception as e:
        logger.warning("Gemini Vision falló para %s: %s", path.name, e)
        return ""


# ── OCR local con Tesseract (gratis, sin API) ─────────────────────────────────

def extract_text_via_tesseract(path: str | Path) -> str:
    """
    OCR local con Tesseract. Soporta PDF (vía pdf2image) e imágenes.
    Requiere binarios del sistema: tesseract y poppler.
    Devuelve "" si no está instalado o falla.
    """
    p = Path(path)
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        logger.info("pytesseract no instalado — saltando OCR local")
        return ""

    try:
        if p.suffix.lower() == ".pdf":
            try:
                from pdf2image import convert_from_path
            except ImportError:
                logger.info("pdf2image no instalado — saltando OCR de PDF")
                return ""
            images = convert_from_path(str(p), dpi=200)
            text_parts = []
            for img in images:
                t = pytesseract.image_to_string(img, lang="spa")
                if t.strip():
                    text_parts.append(t)
            text = "\n\n".join(text_parts).strip()
            if text:
                logger.info("Tesseract extrajo %d chars de %s (PDF)", len(text), p.name)
            return text
        if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".heic"):
            img = Image.open(str(p))
            text = pytesseract.image_to_string(img, lang="spa").strip()
            if text:
                logger.info("Tesseract extrajo %d chars de %s (img)", len(text), p.name)
            return text
        return ""
    except pytesseract.TesseractNotFoundError:
        logger.info("Tesseract binario no encontrado en el sistema — saltando OCR")
        return ""
    except Exception as e:
        logger.warning("Tesseract falló para %s: %s", p.name, e)
        return ""


def extract_text_with_source(
    path: str | Path,
    gemini_api_key: str | None = None,
    gemini_model: str = "gemini-2.0-flash-lite",
) -> tuple[str, str, str | None]:
    """
    Pipeline en cascada de 3 capas con tracking de qué capa funcionó.

    Returns: (texto, fuente, error)
      fuente ∈ {"local", "tesseract", "gemini_vision", "failed"}
      error: descripción del error si fuente == "failed", None en caso contrario
    """
    p = Path(path)
    ext = p.suffix.lower()

    # ── Capa 0: formatos de texto puro (siempre local) ──
    if ext in (".md", ".txt", ".markdown"):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
            if text.strip():
                logger.info("Texto plano: %d chars de %s", len(text), p.name)
                return text, "local", None
            return "", "failed", "Archivo de texto vacío"
        except Exception as e:
            return "", "failed", f"Error leyendo texto: {e}"

    # ── Capa 1: extracción local con librería ──
    local_text = ""
    local_error: str | None = None
    try:
        if ext == ".pdf":
            local_text = extract_text_pdf(p)
        elif ext in (".docx", ".doc"):
            local_text = extract_text_docx(p)
        elif ext in (".xlsx", ".xls"):
            local_text = extract_text_excel(p)
    except Exception as e:
        local_error = f"Librería local falló: {e}"
        logger.warning("Extracción local falló para %s: %s", p.name, e)

    if len(local_text.strip()) >= _MIN_TEXT_CHARS:
        logger.info("Capa 1 OK: %d chars locales de %s", len(local_text), p.name)
        return local_text, "local", None

    logger.info(
        "Capa 1 insuficiente (%d chars) para %s — probando Tesseract",
        len(local_text.strip()), p.name,
    )

    # ── Capa 2: OCR local con Tesseract ──
    if ext == ".pdf" or ext in (".jpg", ".jpeg", ".png", ".heic", ".webp"):
        tess_text = extract_text_via_tesseract(p)
        if len(tess_text.strip()) >= _MIN_TEXT_CHARS:
            return tess_text, "tesseract", None

    # ── Capa 3: Gemini Vision (último recurso, requiere API key) ──
    if ext == ".pdf" or ext in (".jpg", ".jpeg", ".png", ".heic", ".webp"):
        if gemini_api_key:
            vision_text = extract_text_via_vision(p, gemini_api_key, gemini_model)
            if vision_text.strip():
                return vision_text, "gemini_vision", None
        else:
            local_error = local_error or "AI_PROVIDER no configurado y OCR local no extrajo texto"

    # ── Fallback final ──
    if local_text.strip():
        # Texto corto pero algo es algo
        return local_text, "local", None

    return "", "failed", local_error or f"Formato {ext} no procesable o sin texto extraíble"


def extract_text(
    path: str | Path,
    gemini_api_key: str | None = None,
    gemini_model: str = "gemini-2.0-flash-lite",
) -> str:
    """Compat: devuelve solo el texto, sin info de fuente."""
    text, _, _ = extract_text_with_source(path, gemini_api_key, gemini_model)
    return text


# ── NER / entity extraction ───────────────────────────────────────────────────

# Solo regex de alta precisión. Para municipio/departamento/pueblo_indigena
# se delega a la IA (Gemini/Claude/OpenAI) que extrae sin ruido.
_PATTERNS = {
    "nit": re.compile(r"\bNIT[:\s]*(\d[\d.\-]+\d)\b", re.IGNORECASE),
    "fecha": re.compile(
        r"\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\d{1,2} de \w+ de \d{4})\b",
        re.IGNORECASE,
    ),
}


def _chunk_text(text: str, max_chars: int = 100_000) -> Generator[str, None, None]:
    """Split very long texts to respect spaCy's text length limit."""
    for i in range(0, len(text), max_chars):
        yield text[i : i + max_chars]


def extract_entities(text: str, model_name: str = "es_core_news_lg") -> list[dict]:
    """
    Run spaCy NER on the text and return a list of entity dicts with
    {tipo_dato, valor, confianza}.
    """
    nlp = _get_nlp(model_name)
    entities: list[dict] = []

    seen: set[tuple[str, str]] = set()
    for chunk in _chunk_text(text):
        doc = nlp(chunk)
        for ent in doc.ents:
            if ent.label_ not in ("PER", "ORG", "LOC", "GPE", "MISC"):
                continue
            valor = ent.text.strip()
            # Filtrar chunks ruidosos: muy largos, multi-línea o con frases enteras
            if not valor or len(valor) > 60 or "\n" in valor:
                continue
            if len(valor.split()) > 5:
                continue
            tipo = f"ner_{ent.label_.lower()}"
            key = (tipo, valor.lower())
            if key in seen:
                continue
            seen.add(key)
            entities.append({
                "tipo_dato": tipo,
                "valor": valor,
                "confianza": round(ent._.get("score", 0.85), 3) if ent.has_extension("score") else 0.85,
            })

    # Pattern-based extraction (higher precision)
    for tipo, pattern in _PATTERNS.items():
        for match in pattern.finditer(text):
            value = (match.group(1) if match.lastindex else match.group(0)).strip()
            if value:
                entities.append({"tipo_dato": tipo, "valor": value, "confianza": 0.95})

    return entities


# ── Population figures ────────────────────────────────────────────────────────

_POBLACION_RE = re.compile(
    r"(?:poblaci[oó]n|habitantes|personas|familias)[:\s]*"
    r"(\d[\d.,]*)(?:\s*(?:personas|habitantes|familias))?",
    re.IGNORECASE,
)


def extract_population_figures(text: str) -> list[dict]:
    """Extract all population-related numbers mentioned in a document."""
    results = []
    for match in _POBLACION_RE.finditer(text):
        raw = match.group(1).replace(".", "").replace(",", "")
        try:
            n = int(raw)
            context = text[max(0, match.start() - 40) : match.end() + 40]
            results.append(
                {"tipo_dato": "poblacion", "valor": str(n), "confianza": 0.9, "contexto": context}
            )
        except ValueError:
            pass
    return results


# ── Full document pipeline ────────────────────────────────────────────────────

def process_document(
    path: str | Path,
    source_name: str | None = None,
    model_name: str = "es_core_news_lg",
    gemini_api_key: str | None = None,
    gemini_model: str = "gemini-2.0-flash-lite",
) -> dict:
    """
    Extract text + entities from a single document using a 3-layer cascade:
      1. Local library (pdfplumber, docx, openpyxl)
      2. Tesseract OCR (gratis, fallback para PDFs escaneados/imágenes)
      3. Gemini Vision (último recurso si capas 1 y 2 fallan)

    Returns:
        {
            'texto': str,
            'entidades': list[dict],
            'n_caracteres': int,
            'fuente_extraccion': 'local'|'tesseract'|'gemini_vision'|'failed',
            'error_detalle': str | None
        }
    """
    path = Path(path)
    source = source_name or path.name
    text, fuente, error = extract_text_with_source(
        path, gemini_api_key=gemini_api_key, gemini_model=gemini_model,
    )
    entities = extract_entities(text, model_name) if text.strip() else []
    population = extract_population_figures(text) if text.strip() else []

    for e in entities + population:
        e["fuente_archivo"] = source

    return {
        "texto": text,
        "entidades": entities + population,
        "n_caracteres": len(text),
        "fuente_extraccion": fuente,
        "error_detalle": error,
    }
