"""
Prompts dirigidos por tipo de archivo (Sprint Drive C).

Cada rol_en_corpus tiene un prompt corto que pide ÚNICAMENTE los campos del
esquema correspondiente del Sprint Drive B (app/documents/doc_schemas.py).
La IA responde un JSON object (no array) que se valida y guarda en
study_corpus.datos_estructurados.

Diseño:
  - Prompts cortos: la IA recibe solo los campos del rol que está procesando,
    no la lista universal de 50 campos del pipeline viejo.
  - Una sola llamada cuando el texto cabe; chunking jerárquico cuando no.
  - El extractor decide el modelo según preference (Sprint F formaliza esto).
"""
from __future__ import annotations

import json
from typing import Any

from app.documents.doc_schemas import schema_template


# ── Prompt base para extracción dirigida ──────────────────────────────────────

_PROMPT_BASE = """Eres un asistente que extrae datos estructurados de un documento de un estudio etnológico colombiano para reconocimiento de cabildo indígena ante el Ministerio del Interior.

Documento: "{filename}"
Tipo de documento: {tipo_legible}

TAREA: Lee el texto del documento (abajo) y devuelve un único JSON object con los campos especificados en el esquema. Si un campo no aparece en el texto, ponlo en null (o lista vacía para campos de tipo lista). NO inventes datos. NO añadas campos que no estén en el esquema.

ESQUEMA ESPERADO (responde EXACTAMENTE con esta estructura, llenando los valores con lo que encuentres en el texto):

```json
{schema_json}
```

REGLAS:
- Responde SOLO el JSON, sin texto antes ni después, sin bloques de código (```), sin explicaciones.
- Para fechas usa formato YYYY-MM-DD si es posible.
- Para cifras numéricas usa números, no strings ("personas": 287, no "287").
- Para coordenadas convierte DMS a decimal si el texto las da en grados/minutos/segundos.
- Para listas: agrega tantos elementos como encuentres, deduplicados; si no hay, deja [].
- Si el documento es muy corto o no tiene información, devuelve el esquema con valores null/vacío. No te niegues a responder.

{contexto_adicional}

TEXTO DEL DOCUMENTO:
{text}
"""


# Pistas extra por tipo (orienta la atención de la IA)
_CONTEXTO_POR_ROL: dict[str, str] = {
    "ficha_precampo": (
        "Esta ficha contiene la información básica de la comunidad antes del trabajo de campo. "
        "Pon atención a coordenadas, autoridades con sus contactos y evolución demográfica."
    ),
    "reglamento": (
        "El reglamento define la estructura del cabildo. Identifica todos los cargos, "
        "principios fundacionales (tabaco/coca/yuca dulce u otros), cuotas y multas con sus montos."
    ),
    "acta_eleccion": (
        "Para 'cargos_elegidos' incluye cada cargo electo con nombre y cédula. "
        "El 'avalado_por' suele ser la Alcaldía o ACOTRI."
    ),
    "acta_posesion": (
        "Identifica al alcalde o autoridad que toma la posesión, fecha exacta, y la vigencia del periodo en años."
    ),
    "autocenso": (
        "Para distribuciones por edad usa rangos como '0-5', '6-17', '18-60', '60+'. "
        "Si hay una discrepancia con un censo previo, anótala literal."
    ),
    "autocenso_depurado": (
        "Mismo esquema que autocenso. La diferencia es que este pasó por depuración: "
        "anota qué personas se removieron y por qué."
    ),
    "censo_comunidad": (
        "Censo formal (DANE u otro). Anota fuente y año explícitos."
    ),
    "resena_historica": (
        "Para 'eventos_historicos' lista cada hito con su año si aparece. "
        "Los clanes suelen tener traducción en lengua propia — inclúyela."
    ),
    "ficha_comision": (
        "Separa los hallazgos por dimensión: intrarelacional (cultura/rituales/territorio), "
        "interrelacional (relaciones externas), espiritual, territorial, organizativo."
    ),
    "diario_campo": (
        "Para 'entradas', extrae cada día como un objeto con fecha, lugar y narrativa. "
        "Si el diario cubre varios días, cada entrada es un elemento de la lista."
    ),
    "acta_inicio": (
        "Identifica el alcance del estudio, las partes que lo firman y sus compromisos."
    ),
    "arbol_riesgo": (
        "Separa amenazas externas (de fuera de la comunidad) de internas. "
        "Para 'mitigaciones_propuestas' anota acción, responsable y plazo si están."
    ),
    "registro_asistencia": (
        "Cada asistente debe ir con su cédula si aparece. Cuenta el total."
    ),
    "apuntes_reuniones": (
        "Separa temas tratados, acuerdos y próximos pasos. "
        "No mezcles los tres en una sola lista."
    ),
    "generico": (
        "Este documento no tiene un tipo claro asignado. Extrae solo lo evidente: "
        "fecha, autor, datos clave, personas y lugares mencionados, cifras relevantes."
    ),
}


_TIPO_LEGIBLE: dict[str, str] = {
    "ficha_precampo":       "Ficha de Pre-campo",
    "reglamento":           "Reglamento Interno",
    "acta_eleccion":        "Acta de Elección",
    "acta_posesion":        "Acta de Posesión",
    "autocenso":            "Autocenso",
    "autocenso_depurado":   "Autocenso Depurado",
    "censo_comunidad":      "Censo de la Comunidad",
    "resena_historica":     "Reseña Histórica",
    "ficha_comision":       "Ficha de Comisión",
    "diario_campo":         "Diario de Campo",
    "acta_inicio":          "Acta de Inicio",
    "arbol_riesgo":         "Árbol de Riesgos",
    "registro_asistencia":  "Registro de Asistencia",
    "apuntes_reuniones":    "Apuntes de Reuniones",
    "generico":             "Documento sin tipo definido",
}


# ── Roles soportados por extracción dirigida ──────────────────────────────────

# Estos son los roles para los que tenemos esquema en doc_schemas.py.
# Otros (geopackage, proyecto_qgis, evidencia_foto, cronograma, etc.) NO pasan
# por IA: son procesados por motores específicos o ignorados.
ROLES_CON_EXTRACTOR: set[str] = {
    "ficha_precampo", "reglamento", "acta_eleccion", "acta_posesion",
    "autocenso", "autocenso_depurado", "censo_comunidad",
    "resena_historica", "ficha_comision", "diario_campo",
    "acta_inicio", "arbol_riesgo", "registro_asistencia", "apuntes_reuniones",
    "generico",
}


# Roles que NO se procesan con IA (SIG, fotos sin texto, cronogramas)
ROLES_SIN_IA: set[str] = {
    "geopackage", "proyecto_qgis", "evidencia_foto", "cronograma",
    "concepto_etnologico", "borrador_acto_administrativo",
}


# Preferencia de modelo por rol (Sprint F la usará para enrutar al modelo barato/caro)
MODEL_PREFERENCE: dict[str, str] = {
    # Estructurados rígidos → modelo rápido/barato
    "autocenso":            "rapido",
    "autocenso_depurado":   "rapido",
    "censo_comunidad":      "rapido",
    "registro_asistencia":  "rapido",
    "acta_eleccion":        "rapido",
    "acta_posesion":        "rapido",
    "acta_inicio":          "rapido",
    "rut_comunidad":        "rapido",
    # Narrativos → modelo de calidad
    "ficha_precampo":       "calidad",
    "reglamento":           "calidad",
    "resena_historica":     "calidad",
    "ficha_comision":       "calidad",
    "diario_campo":         "calidad",
    "arbol_riesgo":         "calidad",
    "apuntes_reuniones":    "calidad",
    "generico":             "rapido",
}


# ── Builder de prompts ────────────────────────────────────────────────────────

def build_extraction_prompt(rol: str | None, filename: str, text: str) -> str:
    """Construye el prompt de extracción para un archivo dado su rol y texto."""
    rol_efectivo = rol if (rol in ROLES_CON_EXTRACTOR) else "generico"
    template = schema_template(rol_efectivo)
    schema_json = json.dumps(template, indent=2, ensure_ascii=False)
    return _PROMPT_BASE.format(
        filename=filename,
        tipo_legible=_TIPO_LEGIBLE.get(rol_efectivo, rol_efectivo),
        schema_json=schema_json,
        contexto_adicional=_CONTEXTO_POR_ROL.get(rol_efectivo, ""),
        text=text,
    )


# ── Prompt de reduce para chunking jerárquico ─────────────────────────────────

_PROMPT_REDUCE = """Recibiste varios extractos JSON parciales del documento "{filename}" (tipo: {tipo_legible}).

Cada extracto cubre una porción distinta del documento. Tu tarea es FUSIONARLOS en un solo JSON object que cumpla EXACTAMENTE este esquema:

```json
{schema_json}
```

REGLAS DE FUSIÓN:
- Campos primitivos (strings, números, fechas): si dos extractos dan valores distintos, conserva el que parezca más completo o explícito. Si uno es null, usa el otro.
- Listas: une todas las entradas y elimina duplicados (mismo nombre/cédula/fecha cuentan como el mismo).
- Si hay contradicciones obvias (ej. dos fechas distintas para el mismo evento), prefiere la primera y anota la discrepancia en "extra.discrepancias".
- Responde SOLO el JSON fusionado, sin explicación, sin bloques de código.

EXTRACTOS PARCIALES:
{partials_json}
"""


def build_reduce_prompt(rol: str | None, filename: str, partials: list[dict]) -> str:
    rol_efectivo = rol if (rol in ROLES_CON_EXTRACTOR) else "generico"
    template = schema_template(rol_efectivo)
    return _PROMPT_REDUCE.format(
        filename=filename,
        tipo_legible=_TIPO_LEGIBLE.get(rol_efectivo, rol_efectivo),
        schema_json=json.dumps(template, indent=2, ensure_ascii=False),
        partials_json=json.dumps(partials, indent=2, ensure_ascii=False),
    )
