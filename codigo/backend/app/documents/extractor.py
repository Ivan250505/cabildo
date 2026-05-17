"""
Document extraction pipeline.
Reads PDFs, DOCX, and XLSX files and extracts structured text
and ethnological entities via spaCy NER.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Generator

import pdfplumber
import spacy
from docx import Document as DocxDocument

# Lazy-load the spaCy model to avoid loading it at import time
_nlp: spacy.language.Language | None = None


def _get_nlp(model_name: str = "es_core_news_lg") -> spacy.language.Language:
    global _nlp
    if _nlp is None:
        _nlp = spacy.load(model_name)
    return _nlp


# ── Text extraction ───────────────────────────────────────────────────────────

def extract_text_pdf(path: str | Path) -> str:
    """Extract all text from a PDF, page by page."""
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


def extract_text(path: str | Path) -> str:
    """Dispatch to the right extractor based on file extension."""
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".pdf":
        return extract_text_pdf(p)
    if ext in (".docx", ".doc"):
        return extract_text_docx(p)
    raise ValueError(f"Unsupported document format: {ext}")


# ── NER / entity extraction ───────────────────────────────────────────────────

# Patterns for ethnological data
_PATTERNS = {
    "nit": re.compile(r"\bNIT[:\s]*(\d[\d.\-]+\d)\b", re.IGNORECASE),
    "fecha": re.compile(
        r"\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\d{1,2} de \w+ de \d{4})\b",
        re.IGNORECASE,
    ),
    "municipio": re.compile(
        r"\b(?:municipio|ciudad|localidad)\s+(?:de\s+)?([A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+)\b",
        re.IGNORECASE,
    ),
    "departamento": re.compile(
        r"\b(?:departamento)\s+(?:de\s+)?([A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+)\b",
        re.IGNORECASE,
    ),
    "pueblo_indigena": re.compile(
        r"\b(?:pueblo|etnia|comunidad|resguardo)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+)\b",
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

    for chunk in _chunk_text(text):
        doc = nlp(chunk)
        for ent in doc.ents:
            if ent.label_ in ("PER", "ORG", "LOC", "GPE", "MISC"):
                entities.append(
                    {
                        "tipo_dato": f"ner_{ent.label_.lower()}",
                        "valor": ent.text.strip(),
                        "confianza": round(ent._.get("score", 0.85), 3)
                        if ent.has_extension("score")
                        else 0.85,
                    }
                )

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
) -> dict:
    """
    Extract text + entities from a single document.
    Returns {'texto': str, 'entidades': list[dict]}.
    """
    path = Path(path)
    source = source_name or path.name
    text = extract_text(path)
    entities = extract_entities(text, model_name)
    population = extract_population_figures(text)

    for e in entities + population:
        e["fuente_archivo"] = source

    return {
        "texto": text,
        "entidades": entities + population,
        "n_caracteres": len(text),
    }
