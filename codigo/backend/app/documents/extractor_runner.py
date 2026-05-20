"""
Runner de extracción dirigida (Sprint Drive C).

Una sola función pública: extract_for_role(text, filename, rol, ai_extractor) -> dict.

Si el texto cabe en una llamada, una sola pasada (no más extend ciego del pipeline viejo).
Si no cabe, chunking jerárquico:
  - Map: cada chunk produce un JSON parcial usando el mismo prompt dirigido.
  - Reduce: la IA fusiona los parciales en un único JSON cumpliendo el esquema.

No hace flatten ni guardado — eso es responsabilidad del pipeline (Sprint B
ya tiene save_structured_data).
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

from app.documents.doc_schemas import schema_template
from app.documents.extractor_prompts import (
    ROLES_CON_EXTRACTOR, build_extraction_prompt, build_reduce_prompt,
)


# Texto que cabe en una sola llamada sin chunking (chars, no tokens).
# Conservador: deja margen para el prompt completo y la respuesta JSON.
MAX_TEXT_CHARS_SINGLE = 60_000

# Tamaño objetivo de cada chunk en chunking jerárquico
CHUNK_SIZE = 40_000

# Tokens máximos en la respuesta IA. Suficiente para JSON con listas medianas.
MAX_TOKENS_RESPUESTA = 4096


# ── Llamada IA cruda ──────────────────────────────────────────────────────────

def _invoke_ai_json(ai_extractor, prompt: str, max_tokens: int = MAX_TOKENS_RESPUESTA) -> str:
    """
    Llama al cliente IA con un prompt y devuelve el texto crudo.
    Soporta ClaudeExtractor / OpenAIExtractor / GeminiExtractor.
    """
    cls_name = type(ai_extractor).__name__
    if cls_name == "ClaudeExtractor":
        msg = ai_extractor._client.messages.create(
            model=ai_extractor._model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return (msg.content[0].text or "") if msg.content else ""
    if cls_name == "OpenAIExtractor":
        resp = ai_extractor._client.chat.completions.create(
            model=ai_extractor._model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0,
        )
        return resp.choices[0].message.content or ""
    if cls_name == "GeminiExtractor":
        return ai_extractor._generate(prompt) or ""
    raise RuntimeError(f"Proveedor IA no soportado: {cls_name}")


# ── Parseo robusto del JSON object ────────────────────────────────────────────

_FENCE_RE = re.compile(r"```(?:json)?\s*(.+?)\s*```", re.DOTALL | re.IGNORECASE)


def _strip_fences(raw: str) -> str:
    """Si la respuesta viene con ```json ... ```, extrae el contenido."""
    m = _FENCE_RE.search(raw)
    return m.group(1) if m else raw


def _find_json_object(raw: str) -> str | None:
    """Devuelve la sub-cadena del primer JSON object balanceado en raw, o None."""
    if not raw:
        return None
    raw = _strip_fences(raw).strip()
    start = raw.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(raw)):
        c = raw[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return raw[start : i + 1]
    return None


def _safe_parse_object(raw: str) -> dict | None:
    """Extrae el primer JSON object del texto. None si no se puede parsear."""
    chunk = _find_json_object(raw)
    if not chunk:
        return None
    try:
        data = json.loads(chunk)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError as e:
        logger.warning("JSON inválido en respuesta IA: %s (primeros 120 chars: %r)", e, chunk[:120])
    return None


# ── Chunking ──────────────────────────────────────────────────────────────────

def _chunk_text(text: str, size: int = CHUNK_SIZE) -> list[str]:
    """Parte el texto en bloques de 'size' chars intentando cortar en saltos de línea."""
    if len(text) <= size:
        return [text]
    chunks: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        end = min(i + size, n)
        if end < n:
            # Intentar cortar en \n más cercano hacia atrás
            cut = text.rfind("\n", i + int(size * 0.7), end)
            if cut > i:
                end = cut
        chunk = text[i:end].strip()
        if chunk:
            chunks.append(chunk)
        i = end
    return chunks


# ── Pipeline de extracción dirigida ───────────────────────────────────────────

def extract_for_role(
    text: str,
    filename: str,
    rol: str | None,
    ai_extractor,
) -> tuple[dict | None, dict]:
    """
    Extrae datos estructurados según el rol del archivo.

    Returns:
        (datos_json, meta) donde meta tiene:
            { llamadas_ia: int, modo: 'single'|'map_reduce'|'sin_ia',
              error: str|None, modelo: str|None }

    datos_json es el JSON object devuelto por la IA, ya parseado. Puede ser None
    si la IA falló o respondió algo no parseable. El validador del Sprint B se
    encarga de normalizarlo después.
    """
    meta: dict[str, Any] = {
        "llamadas_ia": 0,
        "modo": "sin_ia",
        "error": None,
        "modelo": None,
    }

    if not text or not text.strip():
        meta["error"] = "texto vacío"
        return None, meta

    if ai_extractor is None:
        meta["error"] = "AI_PROVIDER no configurado"
        return None, meta

    # Anotar el modelo usado (acceso por nombre porque cada extractor lo expone distinto)
    meta["modelo"] = getattr(ai_extractor, "_model", None) or getattr(ai_extractor, "_model_name", None)

    rol_efectivo = rol if (rol in ROLES_CON_EXTRACTOR) else "generico"

    # ── Modo single: texto cabe en una sola llamada ──
    if len(text) <= MAX_TEXT_CHARS_SINGLE:
        meta["modo"] = "single"
        prompt = build_extraction_prompt(rol_efectivo, filename, text)
        try:
            raw = _invoke_ai_json(ai_extractor, prompt)
            meta["llamadas_ia"] = 1
        except Exception as e:
            meta["error"] = f"llamada IA falló: {e}"
            logger.warning("Extracción IA falló para %s: %s", filename, e)
            return None, meta
        data = _safe_parse_object(raw)
        if data is None:
            meta["error"] = "respuesta IA no parseable"
            return None, meta
        return data, meta

    # ── Modo map+reduce: chunking jerárquico ──
    meta["modo"] = "map_reduce"
    chunks = _chunk_text(text)
    logger.info("Chunking jerárquico para %s: %d chunks", filename, len(chunks))

    partials: list[dict] = []
    for idx, ch in enumerate(chunks, start=1):
        prompt = build_extraction_prompt(rol_efectivo, f"{filename} (parte {idx}/{len(chunks)})", ch)
        try:
            raw = _invoke_ai_json(ai_extractor, prompt)
            meta["llamadas_ia"] += 1
        except Exception as e:
            logger.warning("Chunk %d/%d falló para %s: %s", idx, len(chunks), filename, e)
            continue
        partial = _safe_parse_object(raw)
        if partial:
            partials.append(partial)

    if not partials:
        meta["error"] = "ningún chunk produjo JSON válido"
        return None, meta

    if len(partials) == 1:
        # Un solo parcial sirvió — no hace falta reducir
        return partials[0], meta

    # Reduce
    reduce_prompt = build_reduce_prompt(rol_efectivo, filename, partials)
    try:
        raw = _invoke_ai_json(ai_extractor, reduce_prompt, max_tokens=MAX_TOKENS_RESPUESTA * 2)
        meta["llamadas_ia"] += 1
    except Exception as e:
        logger.warning("Reduce IA falló para %s: %s — usando merge local", filename, e)
        return _local_merge(partials, rol_efectivo), meta

    final = _safe_parse_object(raw)
    if final is None:
        logger.warning("Reduce devolvió JSON no parseable para %s — usando merge local", filename)
        return _local_merge(partials, rol_efectivo), meta
    return final, meta


# ── Fallback: merge local cuando el reduce IA falla ──────────────────────────

def _local_merge(partials: list[dict], rol: str) -> dict:
    """Merge programático de parciales. No tan bueno como reduce IA, pero salva el archivo."""
    template = schema_template(rol)
    result: dict[str, Any] = {k: ([] if isinstance(v, list) else (None if not isinstance(v, dict) else {})) for k, v in template.items()}

    for partial in partials:
        if not isinstance(partial, dict):
            continue
        for key, expected in template.items():
            val = partial.get(key)
            if val is None or val == [] or val == {} or val == "":
                continue
            if isinstance(expected, list):
                # Listas: extend (la dedup la hace validate_and_normalize después)
                if isinstance(val, list):
                    result[key].extend(val)
            elif isinstance(expected, dict):
                # Dicts anidados: merge superficial
                if isinstance(val, dict) and isinstance(result[key], dict):
                    for sub_k, sub_v in val.items():
                        if sub_v not in (None, "") and result[key].get(sub_k) in (None, ""):
                            result[key][sub_k] = sub_v
            else:
                # Primitivos: primer no-vacío gana
                if result[key] in (None, ""):
                    result[key] = val
    return result
