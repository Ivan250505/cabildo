"""
Generador de texto narrativo para las secciones del informe etnológico.
Usa el mismo proveedor configurado en AI_PROVIDER / AI_API_KEY.
Retorna {} si el proveedor es 'none' o si la API falla.
"""
from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)

_PROMPT = """Eres un etnólogo del Ministerio del Interior de Colombia especializado en estudios de reconocimiento de comunidades indígenas.

Debes redactar las secciones narrativas de un estudio etnológico formal para el proceso de reconocimiento ante la Dirección de Asuntos Indígenas, ROM y Minorías (DAIRM).

DATOS DEL ESTUDIO:
{study_info}

INFORMACIÓN EXTRAÍDA DEL CORPUS DOCUMENTAL (datos reales recopilados en campo):
{extracciones}

INSTRUCCIONES:
- Redacta en español formal-académico, apropiado para un documento oficial del Ministerio del Interior.
- Basa el contenido EXCLUSIVAMENTE en los datos proporcionados. No inventes información.
- Si no hay datos para una sección, escribe un párrafo indicando que la información reposa en el corpus documental anexo.
- Cada sección debe tener entre 2 y 4 párrafos densos y bien argumentados.
- Usa terminología técnica etnológica y jurídica colombiana.

Responde ÚNICAMENTE con un objeto JSON válido con estas claves exactas (sin texto adicional antes o después):
{{
  "historia": "Historia de la comunidad, origen, proceso de asentamiento y antecedentes del reconocimiento",
  "practicas_culturales": "Prácticas culturales, saberes ancestrales, tradiciones y expresiones propias",
  "expresiones_simbolicas": "Expresiones simbólicas, rituales, lengua, cosmovisión y elementos identitarios",
  "entornos_territoriales": "Territorio, sitios sagrados, relación con la tierra y el entorno natural",
  "procesos_organizativos": "Estructura organizativa, autoridades tradicionales, gobierno propio y normativa interna",
  "conclusiones": "Conclusiones del análisis etnológico y recomendaciones para el proceso de reconocimiento formal"
}}"""


def _format_study_info(study_data: dict) -> str:
    campos = [
        ("Comunidad", "nombre_comunidad"),
        ("Pueblo indígena", "pueblo_indigena"),
        ("Municipio", "municipio"),
        ("Departamento", "departamento"),
        ("Vereda", "vereda"),
        ("NIT", "nit_comunidad"),
        ("Contrato de referencia", "contrato_referencia"),
        ("Notas adicionales", "notas_adicionales"),
    ]
    lines = []
    for label, key in campos:
        v = study_data.get(key)
        if v:
            lines.append(f"- {label}: {v}")
    return "\n".join(lines) if lines else "- (datos básicos no disponibles)"


def _format_extracciones(extracciones: list[dict]) -> str:
    by_tipo: dict[str, list[str]] = {}
    for e in extracciones:
        tipo = e.get("tipo_dato", "otro")
        valor = (e.get("valor") or "").strip()
        if valor and len(valor) > 1:
            by_tipo.setdefault(tipo, []).append(valor)

    if not by_tipo:
        return "- (corpus aún no procesado o sin datos extraídos)"

    lines = []
    for tipo, valores in sorted(by_tipo.items()):
        uniques = list(dict.fromkeys(valores))[:8]
        lines.append(f"- {tipo}: {' | '.join(uniques)}")
    return "\n".join(lines)


def _parse_sections(raw: str) -> dict[str, str]:
    raw = raw.strip()
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        return {}
    try:
        data = json.loads(match.group())
        if isinstance(data, dict):
            return {k: str(v).strip() for k, v in data.items() if v and str(v).strip()}
    except (json.JSONDecodeError, ValueError):
        pass
    return {}


def _call(provider: str, api_key: str, model: str, prompt: str) -> str:
    p = provider.lower().strip()

    if p == "claude":
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=model or "claude-haiku-4-5-20251001",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text if msg.content else ""

    if p in ("openai", "chatgpt"):
        import openai
        client = openai.OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model or "gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            temperature=0.3,
        )
        return resp.choices[0].message.content or ""

    if p == "gemini":
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        m = genai.GenerativeModel(model or "gemini-1.5-flash")
        return m.generate_content(prompt).text or ""

    return ""


def generate_sections(
    study_data: dict,
    extracciones: list[dict],
    provider: str,
    api_key: str,
    model: str,
) -> dict[str, str]:
    """
    Genera texto narrativo para las secciones del informe.
    Retorna {} si provider='none', api_key vacía, o si ocurre un error.
    """
    if not provider or provider.lower() == "none" or not api_key:
        return {}

    prompt = _PROMPT.format(
        study_info=_format_study_info(study_data),
        extracciones=_format_extracciones(extracciones),
    )

    try:
        raw = _call(provider, api_key, model, prompt)
        sections = _parse_sections(raw)
        logger.info("AI writer: %d secciones generadas para %s", len(sections), study_data.get("nombre_comunidad"))
        return sections
    except Exception as exc:
        logger.warning("AI writer falló: %s", exc)
        return {}
