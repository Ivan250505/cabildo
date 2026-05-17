"""
Capa de extracción con IA intercambiable.

Proveedor se selecciona vía config: AI_PROVIDER = claude | openai | gemini | none
Si AI_PROVIDER = "none" o no hay API key, se omite y solo corre spaCy.

Cada proveedor implementa el mismo método:
  extract(text, filename) -> list[dict]  donde cada dict es:
  {"tipo_dato": str, "valor": str, "confianza": float}
"""
from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

# Máximo de caracteres enviados por chunk a la IA (evitar límites de contexto)
_CHUNK_SIZE = 12_000

_PROMPT_TEMPLATE = """Eres un experto en análisis de estudios etnológicos colombianos para el Ministerio del Interior.
El siguiente texto proviene del documento "{filename}" que hace parte del corpus de reconocimiento de un cabildo indígena.

Extrae ÚNICAMENTE datos que estén explícitamente mencionados en el texto. No inventes ni inferis información.

Responde SOLO con un JSON array válido. Cada elemento debe tener exactamente estas tres claves:
{{"tipo_dato": string, "valor": string, "confianza": número entre 0 y 1}}

Tipos de datos a extraer (usa exactamente estos nombres):
- familias_count         → número de familias del cabildo
- personas_count         → número de personas o miembros
- fecha_censo            → fecha del censo o registro
- nombre_comunidad       → nombre del cabildo o comunidad
- pueblo_indigena        → pueblo o etnia indígena
- municipio              → municipio de ubicación
- departamento           → departamento de ubicación
- vereda                 → vereda o corregimiento
- resguardo              → nombre del resguardo (si aplica)
- representante_legal    → nombre del gobernador o representante legal
- nit                    → NIT de la comunidad
- actividad_cultural     → práctica o actividad cultural mencionada
- territorio_descripcion → descripción del territorio o área
- fuente_censo           → institución del censo (DANE, Ministerio, autocenso, cabildo, etc.)
- contrato_referencia    → número o referencia del contrato
- discrepancia_poblacion → descripción de discrepancia entre fuentes de población

Si no encuentras datos de algún tipo, no lo incluyas. Si el texto no contiene datos extraíbles, devuelve [].

Texto a analizar:
{text}"""


def _safe_parse(raw: str) -> list[dict]:
    """Extrae el JSON array de la respuesta del modelo, tolerando texto alrededor."""
    raw = raw.strip()
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group())
        if not isinstance(data, list):
            return []
        validated = []
        for item in data:
            if (
                isinstance(item, dict)
                and "tipo_dato" in item
                and "valor" in item
                and item.get("valor")
                and str(item["valor"]).strip()
            ):
                validated.append({
                    "tipo_dato": str(item["tipo_dato"]),
                    "valor": str(item["valor"]).strip()[:500],
                    "confianza": float(item.get("confianza", 0.9)),
                })
        return validated
    except (json.JSONDecodeError, ValueError):
        return []


def _chunk(text: str, size: int = _CHUNK_SIZE) -> list[str]:
    chunks = []
    for i in range(0, len(text), size):
        chunk = text[i : i + size].strip()
        if chunk:
            chunks.append(chunk)
    return chunks


# ── Base class ────────────────────────────────────────────────────────────────

class AIExtractor(ABC):
    @abstractmethod
    def extract(self, text: str, filename: str) -> list[dict]:
        """Return list of {tipo_dato, valor, confianza} dicts."""


# ── Claude (Anthropic) ────────────────────────────────────────────────────────

class ClaudeExtractor(AIExtractor):
    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def extract(self, text: str, filename: str) -> list[dict]:
        results: list[dict] = []
        for chunk in _chunk(text):
            prompt = _PROMPT_TEMPLATE.format(filename=filename, text=chunk)
            try:
                msg = self._client.messages.create(
                    model=self._model,
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw = msg.content[0].text if msg.content else ""
                results.extend(_safe_parse(raw))
            except Exception as e:
                logger.warning("Claude extraction error on %s: %s", filename, e)
        return results


# ── OpenAI (ChatGPT) ──────────────────────────────────────────────────────────

class OpenAIExtractor(AIExtractor):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        import openai
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model

    def extract(self, text: str, filename: str) -> list[dict]:
        results: list[dict] = []
        for chunk in _chunk(text):
            prompt = _PROMPT_TEMPLATE.format(filename=filename, text=chunk)
            try:
                resp = self._client.chat.completions.create(
                    model=self._model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1024,
                    temperature=0,
                )
                raw = resp.choices[0].message.content or ""
                results.extend(_safe_parse(raw))
            except Exception as e:
                logger.warning("OpenAI extraction error on %s: %s", filename, e)
        return results


# ── Gemini (Google) ───────────────────────────────────────────────────────────

class GeminiExtractor(AIExtractor):
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model)

    def extract(self, text: str, filename: str) -> list[dict]:
        results: list[dict] = []
        for chunk in _chunk(text):
            prompt = _PROMPT_TEMPLATE.format(filename=filename, text=chunk)
            try:
                resp = self._model.generate_content(prompt)
                raw = resp.text or ""
                results.extend(_safe_parse(raw))
            except Exception as e:
                logger.warning("Gemini extraction error on %s: %s", filename, e)
        return results


# ── Factory ───────────────────────────────────────────────────────────────────

def get_ai_extractor(provider: str, api_key: str, model: str) -> AIExtractor | None:
    """
    Returns the right extractor for the configured provider.
    Returns None if provider is 'none' or api_key is empty.
    """
    provider = provider.lower().strip()
    if provider == "none" or not api_key:
        return None
    if provider == "claude":
        return ClaudeExtractor(api_key=api_key, model=model or "claude-haiku-4-5-20251001")
    if provider in ("openai", "chatgpt"):
        return OpenAIExtractor(api_key=api_key, model=model or "gpt-4o-mini")
    if provider == "gemini":
        return GeminiExtractor(api_key=api_key, model=model or "gemini-1.5-flash")
    logger.warning("AI_PROVIDER '%s' no reconocido. Usando solo spaCy.", provider)
    return None
