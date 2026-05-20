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
- Para la sección de conciencia_identidad, enfócate en cómo la comunidad se auto-reconoce como indígena, los elementos diferenciadores y la continuidad cultural.
- Para la caracterizacion_intrarelacional, abarca prácticas culturales, rituales, cosmovisión, territorialidad, lengua y gobierno propio.
- Para la caracterizacion_interrelacional, abarca relaciones con el Estado, instituciones, otras comunidades y actores externos.

Responde ÚNICAMENTE con un objeto JSON válido con estas claves exactas (sin texto adicional antes o después):
{{
  "presentacion": "Presentación del estudio: objetivo, alcance, metodología de campo y marco contractual",
  "resena_historica": "Reseña histórica: origen de la comunidad, trayectoria migratoria, fundadores, proceso de asentamiento y antecedentes del reconocimiento",
  "conciencia_identidad": "Conciencia de identidad: cómo la comunidad se auto-reconoce como pueblo indígena, elementos de diferenciación étnica, continuidad cultural y uso de la lengua",
  "caracterizacion_intrarelacional": "Caracterización intrarelacional: prácticas culturales, rituales, cosmovisión, territorialidad, sitios sagrados, gobierno propio y normas internas",
  "caracterizacion_interrelacional": "Caracterización interrelacional: relaciones con entidades del Estado, instituciones, comunidades vecinas, otros pueblos indígenas y actores externos",
  "prospectiva": "Prospectiva: amenazas identificadas al territorio y la cultura, despojos históricos, visión de futuro y proyectos comunitarios",
  "conclusiones": "Conclusiones del análisis etnológico y recomendaciones para el proceso de reconocimiento formal ante el Ministerio del Interior"
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
        m = genai.GenerativeModel(model or "gemini-2.0-flash-lite")
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
    [Legacy] Genera texto narrativo a partir de la lista plana de extracciones.
    Sigue disponible para retrocompatibilidad. Prefiera generate_sections_from_consolidated.
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
        logger.error("AI writer falló (provider=%s): %s", provider, exc)
        return {}


# ── Pipeline v2 (Sprint Drive E): consume el consolidado ──────────────────────

_PROMPT_V2 = """Eres un etnólogo del Ministerio del Interior de Colombia especializado en estudios de reconocimiento de comunidades indígenas.

Debes redactar las secciones narrativas de un estudio etnológico formal para el proceso de reconocimiento ante la Dirección de Asuntos Indígenas, ROM y Minorías (DAIRM).

DATOS DEL ESTUDIO:
{study_info}

DATOS CONSOLIDADOS DEL CORPUS (estructurados, ya deduplicados, con sus fuentes archivo entre paréntesis cuando aplica):

{consolidated_blocks}

INSTRUCCIONES:
- Redacta en español formal-académico, apropiado para un documento oficial del Ministerio del Interior.
- Usa SOLO los datos arriba. No inventes hechos. Si un dato falta, omítelo o di que la información está en el corpus anexo.
- Cuando cites una cifra o nombre que aparezca con una fuente, menciona la fuente entre paréntesis al estilo "(según Autocenso_2024.xlsx)".
- Cada sección entre 2 y 4 párrafos densos, sin viñetas.
- Terminología técnica etnológica + jurídica colombiana (Constitución 1991, Convenio 169 OIT, Decreto 2164/1995, etc.).

Responde ÚNICAMENTE con un objeto JSON válido con estas claves exactas (sin texto adicional antes/después, sin bloques de código):
{{
  "presentacion": "Presentación del estudio: objetivo, alcance, metodología de campo y marco contractual",
  "resena_historica": "Reseña histórica: origen ancestral, clanes, eventos clave, despojos, proceso de recuperación",
  "conciencia_identidad": "Conciencia de identidad: auto-reconocimiento, lengua, clanes, principios fundacionales, continuidad cultural",
  "caracterizacion_intrarelacional": "Caracterización intrarelacional: prácticas culturales, rituales, lugares sagrados, gobierno propio, estructura de cargos, reglamento interno",
  "caracterizacion_interrelacional": "Caracterización interrelacional: alianzas con otros pueblos, relaciones institucionales (Alcaldía, Ministerio, ONGs), actores externos",
  "prospectiva": "Prospectiva: amenazas internas y externas, despojos históricos, mitigaciones propuestas, visión de futuro",
  "conclusiones": "Conclusiones del análisis etnológico: solidez del reconocimiento, datos poblacionales, territorialidad SIG, y recomendaciones"
}}
"""


def _summarize_list_with_fuente(items: list, max_items: int = 6) -> list[str]:
    """Convierte una lista de dicts del consolidado a líneas con su fuente."""
    out: list[str] = []
    for it in items[:max_items]:
        if not isinstance(it, dict):
            out.append(f"- {it}")
            continue
        fuente = it.get("_fuente") or it.get("fuente") or "—"
        copy = {k: v for k, v in it.items() if not k.startswith("_") and k != "fuente"}
        partes = [f"{k}: {v}" for k, v in copy.items() if v not in (None, "", [], {})]
        line = "; ".join(partes) or "(sin detalles)"
        out.append(f"- {line} (fuente: {fuente})")
    if len(items) > max_items:
        out.append(f"- … y {len(items) - max_items} más")
    return out


def _flatten_val(v):
    if isinstance(v, dict) and "valor" in v:
        return v["valor"]
    return v


def _block_identificacion(c: dict) -> str:
    ident = c.get("identificacion") or {}
    lines = ["[IDENTIFICACIÓN]"]
    for k in ("nombre_comunidad", "autodenominacion", "pueblo_indigena", "municipio",
              "vereda", "departamento", "nit", "representante_legal"):
        v = _flatten_val(ident.get(k))
        if v:
            lines.append(f"- {k}: {v}")
    if ident.get("autoridades"):
        lines.append("- autoridades:")
        lines.extend("  " + s for s in _summarize_list_with_fuente(ident["autoridades"], max_items=8))
    return "\n".join(lines)


def _block_poblacion(c: dict) -> str:
    pob = c.get("poblacion") or {}
    lines = ["[POBLACIÓN]"]
    for k in ("personas", "familias", "fecha_censo", "fuente_censo"):
        v = pob.get(k)
        if isinstance(v, dict):
            lines.append(f"- {k}: {v.get('valor')} (fuente: {v.get('fuente')}, rol: {v.get('rol','-')})")
        elif v not in (None, ""):
            lines.append(f"- {k}: {v}")
    if pob.get("distribucion_por_sexo"):
        d = pob["distribucion_por_sexo"]
        lines.append(f"- distribución por sexo: F={d.get('femenino')} M={d.get('masculino')} otro={d.get('otro')}")
    if pob.get("distribucion_por_edad"):
        for ed in pob["distribucion_por_edad"]:
            lines.append(f"  - edad {ed.get('rango')}: {ed.get('cantidad')}")
    if pob.get("evolucion_demografica"):
        lines.append("- evolución demográfica:")
        for ev in pob["evolucion_demografica"][:6]:
            lines.append(f"  - {ev.get('anio')}: {ev.get('personas','?')} personas, {ev.get('familias','?')} familias")
    if pob.get("discrepancias"):
        lines.append(f"- ⚠ DISCREPANCIAS: {len(pob['discrepancias'])} (resolver antes de afirmar cifras).")
        for d in pob["discrepancias"][:3]:
            lines.append(f"  - {d.get('campo')}: {d.get('valor_a')} (de {d.get('fuente_a')}) vs {d.get('valor_b')} (de {d.get('fuente_b')})")
    return "\n".join(lines)


def _block_historia(c: dict) -> str:
    hist = c.get("historia") or {}
    lines = ["[HISTORIA]"]
    if _flatten_val(hist.get("lugar_origen")):
        lines.append(f"- lugar de origen: {_flatten_val(hist['lugar_origen'])}")
    for cat in ("narrativa_origen", "cosmogonia", "proceso_recuperacion"):
        items = hist.get(cat) or []
        if items:
            lines.append(f"- {cat}:")
            for it in items[:3]:
                texto = (it.get("texto") if isinstance(it, dict) else str(it))[:500]
                fuente = it.get("fuente") if isinstance(it, dict) else "—"
                lines.append(f"  - {texto} (fuente: {fuente})")
    if hist.get("clanes"):
        lines.append("- clanes:")
        lines.extend("  " + s for s in _summarize_list_with_fuente(hist["clanes"]))
    if hist.get("eventos_historicos"):
        lines.append("- eventos históricos:")
        lines.extend("  " + s for s in _summarize_list_with_fuente(hist["eventos_historicos"]))
    if hist.get("elementos_sagrados"):
        lines.append("- elementos sagrados:")
        lines.extend("  " + s for s in _summarize_list_with_fuente(hist["elementos_sagrados"]))
    return "\n".join(lines)


def _block_identidad(c: dict) -> str:
    ident = c.get("identidad") or {}
    lines = ["[IDENTIDAD]"]
    if ident.get("autoidentificacion"):
        lines.append("- autoidentificación:")
        lines.extend("  " + s for s in _summarize_list_with_fuente(ident["autoidentificacion"]))
    if ident.get("clanes"):
        lines.append("- clanes referenciados:")
        lines.extend("  " + s for s in _summarize_list_with_fuente(ident["clanes"]))
    if ident.get("principios_fundacionales"):
        lines.append("- principios fundacionales:")
        lines.extend("  " + s for s in _summarize_list_with_fuente(ident["principios_fundacionales"]))
    return "\n".join(lines)


def _block_intra(c: dict) -> str:
    intra = c.get("caracterizacion_intrarelacional") or {}
    lines = ["[CARACTERIZACIÓN INTRARELACIONAL]"]
    for k in ("estructura_cargos", "instancias_decision", "actividades_culturales",
              "rituales", "lugares_sagrados", "hallazgos_campo"):
        items = intra.get(k) or []
        if items:
            lines.append(f"- {k}:")
            lines.extend("  " + s for s in _summarize_list_with_fuente(items, max_items=6))
    return "\n".join(lines)


def _block_inter(c: dict) -> str:
    inter = c.get("caracterizacion_interrelacional") or {}
    lines = ["[CARACTERIZACIÓN INTERRELACIONAL]"]
    for k in ("alianzas_interetnicas", "relaciones_institucionales",
              "actores_externos", "acuerdos_recientes"):
        items = inter.get(k) or []
        if items:
            lines.append(f"- {k}:")
            lines.extend("  " + s for s in _summarize_list_with_fuente(items))
    return "\n".join(lines)


def _block_prospectiva(c: dict) -> str:
    pros = c.get("prospectiva") or {}
    lines = ["[PROSPECTIVA]"]
    for k in ("amenazas_externas", "amenazas_internas", "causas_raiz",
              "efectos", "mitigaciones_propuestas", "vision_futuro", "despojos_historicos"):
        items = pros.get(k) or []
        if items:
            lines.append(f"- {k}:")
            lines.extend("  " + s for s in _summarize_list_with_fuente(items))
    return "\n".join(lines)


def _block_territorio(c: dict) -> str:
    terr = c.get("territorio_y_sig") or {}
    lines = ["[TERRITORIO Y SIG]"]
    cc = terr.get("coordenadas_centrales") or {}
    if cc.get("lat") is not None and cc.get("lng") is not None:
        lines.append(f"- coordenadas centrales: {cc.get('lat')}, {cc.get('lng')} (plus code: {cc.get('plus_code','-')})")
    if terr.get("vias_acceso"):
        lines.append(f"- vías de acceso: {_flatten_val(terr['vias_acceso'])}")
    if terr.get("ubicaciones"):
        lines.append(f"- ubicaciones georreferenciadas: {len(terr['ubicaciones'])} puntos")
    if terr.get("resultados_sig"):
        lines.append(f"- resultados SIG calculados: {len(terr['resultados_sig'])} análisis")
    return "\n".join(lines)


def _build_consolidated_blocks(consolidated: dict) -> str:
    parts = [
        _block_identificacion(consolidated),
        _block_poblacion(consolidated),
        _block_historia(consolidated),
        _block_identidad(consolidated),
        _block_intra(consolidated),
        _block_inter(consolidated),
        _block_prospectiva(consolidated),
        _block_territorio(consolidated),
    ]
    return "\n\n".join(parts)


def generate_sections_from_consolidated(
    study_data: dict,
    consolidated: dict,
    provider: str,
    api_key: str,
    model: str,
) -> dict[str, str]:
    """
    Versión nueva del writer que consume el consolidado del Sprint Drive E
    en lugar de la lista plana de extracciones. Una sola llamada IA con un
    prompt bien estructurado por sección. Retorna {} si falla o no hay IA.
    """
    if not provider or provider.lower() == "none" or not api_key:
        return {}

    if not consolidated or not isinstance(consolidated, dict):
        return {}

    blocks = _build_consolidated_blocks(consolidated)
    prompt = _PROMPT_V2.format(
        study_info=_format_study_info(study_data),
        consolidated_blocks=blocks,
    )

    try:
        raw = _call(provider, api_key, model, prompt)
        sections = _parse_sections(raw)
        logger.info(
            "AI writer v2: %d secciones generadas para %s (consolidado: %d archivos)",
            len(sections), study_data.get("nombre_comunidad"),
            consolidated.get("metadata", {}).get("archivos_con_datos", 0),
        )
        return sections
    except Exception as exc:
        logger.error("AI writer v2 falló (provider=%s): %s", provider, exc)
        return {}
