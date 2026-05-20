"""
Clasificador de archivos del corpus.

Asigna un rol_en_corpus a cada StudyCorpus mediante una cascada:
  1. Extensión decisiva (.gpkg/.qgz/.shp/.qgs → geopackage / proyecto_qgis)
  2. Pista de carpeta + extensión (foto en /evidencias → evidencia_foto)
  3. Patrón de nombre fuerte (regex específico)
  4. Patrón de nombre débil (palabra suelta)
  5. IA corta sobre las primeras páginas (si se proporciona text_sample y ai_extractor)
  6. Fallback 'otro' con confianza 0

Fuente de verdad del catálogo: DOCUMENTACION/CATALOGO_TIPOS_ARCHIVO.md
Enum de roles: app/studies/models.py::CORPUS_ROLES
"""
from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


# ── Confianza por fuente ──────────────────────────────────────────────────────

CONFIANZA: dict[str, float] = {
    "manual": 1.000,
    "heuristica_extension": 0.950,
    "heuristica_carpeta": 0.850,
    "heuristica_nombre": 0.800,
    "heuristica_nombre_debil": 0.600,
    "ia_inicio": 0.800,
    "fallback_otro": 0.000,
}


@dataclass
class ClassificationResult:
    rol: str
    fuente: str
    confianza: float
    notas: str | None = None


# ── Normalización ─────────────────────────────────────────────────────────────

def _normalize(s: str) -> str:
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFKD", s)
    sin_acentos = "".join(c for c in nfkd if not unicodedata.combining(c))
    return sin_acentos.lower()


# ── Extensiones decisivas ─────────────────────────────────────────────────────

EXTENSION_ROL: dict[str, str] = {
    ".gpkg": "geopackage",
    ".shp": "geopackage",
    ".qgz": "proyecto_qgis",
    ".qgs": "proyecto_qgis",
}

EXTENSIONES_FOTO: set[str] = {".jpg", ".jpeg", ".png", ".heic", ".webp"}


# ── Reglas por carpeta (orden de prioridad) ───────────────────────────────────

CARPETA_HINT: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(evidenc|fotos?|imagenes?)\b"), "evidencia_foto"),
    (re.compile(r"\b(qgis|sig)\b"),                  "geopackage"),
    (re.compile(r"\bcartograf"),                     "cartografia_social"),
    (re.compile(r"\b(censo|padron|padr[oó]n)\b"),    "autocenso"),
    (re.compile(r"\basistencia\b"),                  "registro_asistencia"),
    (re.compile(r"\briesgo"),                        "arbol_riesgo"),
    (re.compile(r"\bcomision\b"),                    "ficha_comision"),
    (re.compile(r"\b(diario|bitacora)\b"),           "diario_campo"),
    (re.compile(r"\b(reunion|minuta|apunte)"),       "apuntes_reuniones"),
    (re.compile(r"\b(historia|resen)"),              "resena_historica"),
    (re.compile(r"\b(reglamento|estatuto)\b"),       "reglamento"),
    (re.compile(r"\b(precampo|pre[_\s-]?campo)\b"),  "ficha_precampo"),
    (re.compile(r"\bdane\b"),                        "base_datos_dane"),
    (re.compile(r"\b(rut|dian)\b"),                  "rut_comunidad"),
]


# ── Reglas por nombre (orden importa: específico primero) ─────────────────────

# Formato: (patrón, rol, "fuerte" | "debil")
NOMBRE_PATRONES: list[tuple[re.Pattern, str, str]] = [
    # Específicos compuestos primero
    (re.compile(r"autocenso[_\s-]*depurado"),                         "autocenso_depurado", "fuerte"),
    (re.compile(r"censo[_\s-]*depurado"),                             "autocenso_depurado", "fuerte"),
    (re.compile(r"acta[_\s-]*(de[_\s-]*)?eleccion"),                  "acta_eleccion",      "fuerte"),
    (re.compile(r"eleccion[_\s-]*autoridades"),                       "acta_eleccion",      "fuerte"),
    (re.compile(r"\bf1[_\s-]*04a\b"),                                 "acta_eleccion",      "fuerte"),
    (re.compile(r"acta[_\s-]*(de[_\s-]*)?posesion"),                  "acta_posesion",      "fuerte"),
    (re.compile(r"posesion[_\s-]*alcaldia"),                          "acta_posesion",      "fuerte"),
    (re.compile(r"\bf1[_\s-]*04b\b"),                                 "acta_posesion",      "fuerte"),
    (re.compile(r"acta[_\s-]*(de[_\s-]*)?inicio"),                    "acta_inicio",        "fuerte"),
    (re.compile(r"acta[_\s-]*apertura"),                              "acta_inicio",        "fuerte"),
    (re.compile(r"\bf2[_\s-]*04\b"),                                  "acta_inicio",        "fuerte"),
    (re.compile(r"ficha[_\s-]*(de[_\s-]*)?pre[_\s-]*campo"),          "ficha_precampo",     "fuerte"),
    (re.compile(r"\bprecampo\b"),                                     "ficha_precampo",     "fuerte"),
    (re.compile(r"\bf1[_\s-]*01\b"),                                  "ficha_precampo",     "fuerte"),
    (re.compile(r"ficha[_\s-]*(de[_\s-]*)?comision"),                 "ficha_comision",     "fuerte"),
    (re.compile(r"\bf2[_\s-]*01\b"),                                  "ficha_comision",     "fuerte"),
    (re.compile(r"comision[_\s-]*campo"),                             "ficha_comision",     "fuerte"),
    (re.compile(r"diario[_\s-]*(de[_\s-]*)?campo"),                   "diario_campo",       "fuerte"),
    (re.compile(r"bitacora[_\s-]*campo"),                             "diario_campo",       "fuerte"),
    (re.compile(r"\bf2[_\s-]*02\b"),                                  "diario_campo",       "fuerte"),
    (re.compile(r"registro[_\s-]*(de[_\s-]*)?asistencia"),            "registro_asistencia", "fuerte"),
    (re.compile(r"lista[_\s-]*asistencia"),                           "registro_asistencia", "fuerte"),
    (re.compile(r"\bf2[_\s-]*03\b"),                                  "registro_asistencia", "fuerte"),
    (re.compile(r"arbol[_\s-]*(de[_\s-]*)?riesgo"),                   "arbol_riesgo",       "fuerte"),
    (re.compile(r"riesgos[_\s-]*comunidad"),                          "arbol_riesgo",       "fuerte"),
    (re.compile(r"\bf2[_\s-]*05\b"),                                  "arbol_riesgo",       "fuerte"),
    (re.compile(r"cartografia[_\s-]*social"),                         "cartografia_social", "fuerte"),
    (re.compile(r"mapa[_\s-]*comunitario"),                           "cartografia_social", "fuerte"),
    (re.compile(r"\bf2[_\s-]*06\b"),                                  "cartografia_social", "fuerte"),
    (re.compile(r"apuntes[_\s-]*reuniones"),                          "apuntes_reuniones",  "fuerte"),
    (re.compile(r"notas[_\s-]*reuniones"),                            "apuntes_reuniones",  "fuerte"),
    (re.compile(r"\bminutas?\b"),                                     "apuntes_reuniones",  "fuerte"),
    (re.compile(r"\bf2[_\s-]*07\b"),                                  "apuntes_reuniones",  "fuerte"),
    (re.compile(r"rese[nñ]a[_\s-]*historica"),                        "resena_historica",   "fuerte"),
    (re.compile(r"historia[_\s-]*(del[_\s-]*)?(pueblo|cabildo|comunidad)"), "resena_historica", "fuerte"),
    (re.compile(r"\bf1[_\s-]*05\b"),                                  "resena_historica",   "fuerte"),
    (re.compile(r"reglamento[_\s-]*interno"),                         "reglamento",         "fuerte"),
    (re.compile(r"\breglamento\b"),                                   "reglamento",         "fuerte"),
    (re.compile(r"\bestatuto\b"),                                     "reglamento",         "fuerte"),
    (re.compile(r"\bf1[_\s-]*02\b"),                                  "reglamento",         "fuerte"),
    (re.compile(r"mapa[_\s-]*territorial"),                           "mapa_territorial",   "fuerte"),
    (re.compile(r"mapa[_\s-]*(del[_\s-]*)?(resguardo|territorio)"),   "mapa_territorial",   "fuerte"),
    (re.compile(r"\bcroquis\b"),                                      "mapa_territorial",   "fuerte"),
    (re.compile(r"\boficio[_\s-]*remisorio\b"),                       "solicitud_formal",   "fuerte"),
    (re.compile(r"\bradicado\b"),                                     "solicitud_formal",   "fuerte"),
    (re.compile(r"base[_\s-]*datos[_\s-]*dane"),                      "base_datos_dane",    "fuerte"),
    (re.compile(r"\bdane\b"),                                         "base_datos_dane",    "fuerte"),
    (re.compile(r"registro[_\s-]*unico[_\s-]*tributario"),            "rut_comunidad",      "fuerte"),
    (re.compile(r"\brut\b"),                                          "rut_comunidad",      "fuerte"),
    (re.compile(r"\bcronograma\b"),                                   "cronograma",         "fuerte"),
    (re.compile(r"plan[_\s-]*trabajo"),                               "cronograma",         "fuerte"),
    (re.compile(r"\bautocenso\b"),                                    "autocenso",          "fuerte"),
    (re.compile(r"auto[_\s-]*censo"),                                 "autocenso",          "fuerte"),
    (re.compile(r"\bf1[_\s-]*03\b"),                                  "autocenso",          "fuerte"),
    (re.compile(r"censo[_\s-]*\d{4}"),                                "censo_comunidad",    "fuerte"),
    (re.compile(r"censo[_\s-]*comunidad"),                            "censo_comunidad",    "fuerte"),
    (re.compile(r"concepto[_\s-]*etnologico"),                        "concepto_etnologico", "fuerte"),
    (re.compile(r"borrador[_\s-]*acto"),                              "borrador_acto_administrativo", "fuerte"),
    (re.compile(r"acto[_\s-]*administrativo"),                        "borrador_acto_administrativo", "fuerte"),

    # Débiles (palabras genéricas)
    (re.compile(r"\bsolicitud\b"),                                    "solicitud_formal",   "debil"),
    (re.compile(r"\bpeticion\b"),                                     "solicitud_formal",   "debil"),
    (re.compile(r"\bdian\b"),                                         "rut_comunidad",      "debil"),
    (re.compile(r"\bcenso\b"),                                        "censo_comunidad",    "debil"),
    (re.compile(r"\bacta\b"),                                         "acta_inicio",        "debil"),
]


# ── Matchers internos ─────────────────────────────────────────────────────────

def _match_extension(file_name: str) -> tuple[str, str] | None:
    ext = Path(file_name).suffix.lower()
    if ext in EXTENSION_ROL:
        return EXTENSION_ROL[ext], "heuristica_extension"
    return None


def _match_carpeta(subfolder: str | None, file_name: str) -> str | None:
    if not subfolder:
        return None
    norm_folder = _normalize(subfolder)
    ext = Path(file_name).suffix.lower()
    if ext in EXTENSIONES_FOTO and re.search(r"\b(evidenc|fotos?|imagenes?)\b", norm_folder):
        return "evidencia_foto"
    for pattern, rol in CARPETA_HINT:
        if pattern.search(norm_folder):
            return rol
    return None


def _match_nombre(file_name: str) -> tuple[str, str] | None:
    norm = _normalize(file_name)
    fuerte: tuple[str, str] | None = None
    debil: tuple[str, str] | None = None
    for pattern, rol, fuerza in NOMBRE_PATRONES:
        if pattern.search(norm):
            if fuerza == "fuerte" and fuerte is None:
                fuerte = (rol, "heuristica_nombre")
            elif fuerza == "debil" and debil is None:
                debil = (rol, "heuristica_nombre_debil")
    return fuerte or debil


# ── Cascada heurística ────────────────────────────────────────────────────────

def classify_heuristic(
    file_name: str,
    subfolder: str | None = None,
) -> ClassificationResult | None:
    """Devuelve un resultado heurístico o None si nada matchea."""
    ext_match = _match_extension(file_name)
    if ext_match:
        rol, fuente = ext_match
        return ClassificationResult(
            rol=rol, fuente=fuente, confianza=CONFIANZA[fuente],
            notas=f"Extensión {Path(file_name).suffix.lower()} → {rol}",
        )

    carpeta_rol = _match_carpeta(subfolder, file_name)
    nombre_match = _match_nombre(file_name)

    if carpeta_rol:
        # Si hay nombre fuerte, gana sobre la carpeta (es más específico)
        if nombre_match and nombre_match[1] == "heuristica_nombre":
            return ClassificationResult(
                rol=nombre_match[0], fuente="heuristica_nombre",
                confianza=CONFIANZA["heuristica_nombre"],
                notas=f"Nombre específico (carpeta sugería '{carpeta_rol}')",
            )
        return ClassificationResult(
            rol=carpeta_rol, fuente="heuristica_carpeta",
            confianza=CONFIANZA["heuristica_carpeta"],
            notas=f"Carpeta '{subfolder}' → {carpeta_rol}",
        )

    if nombre_match:
        rol, fuente = nombre_match
        return ClassificationResult(
            rol=rol, fuente=fuente, confianza=CONFIANZA[fuente],
            notas=f"Patrón de nombre → {rol}",
        )

    return None


# ── Clasificador IA corto ─────────────────────────────────────────────────────

_ROLES_IA: list[str] = [
    "ficha_precampo", "solicitud_formal", "reglamento", "acta_eleccion",
    "acta_posesion", "autocenso_depurado", "autocenso", "censo_comunidad",
    "rut_comunidad", "resena_historica", "mapa_territorial", "base_datos_dane",
    "acta_inicio", "cronograma", "diario_campo", "ficha_comision",
    "apuntes_reuniones", "arbol_riesgo", "cartografia_social",
    "registro_asistencia", "concepto_etnologico", "borrador_acto_administrativo",
    "otro",
]

_PROMPT_CLASIFICADOR = """Eres un asistente que clasifica documentos de un estudio etnológico colombiano.

Mira las primeras líneas del documento "{filename}" y decide a cuál tipo corresponde.

Tipos válidos (responde EXACTAMENTE uno de estos códigos, sin comillas ni puntuación):
{tipos}

Reglas:
- Responde SOLO el código del tipo, una sola palabra.
- Si no puedes decidir con certeza razonable, responde: otro
- No inventes códigos nuevos.

Extracto del documento:
{extracto}
"""


def _invoke_ai_short(ai_extractor, prompt: str) -> str:
    """Invoca el cliente IA del extractor con max_tokens muy bajo (clasificación)."""
    cls_name = type(ai_extractor).__name__
    if cls_name == "ClaudeExtractor":
        msg = ai_extractor._client.messages.create(
            model=ai_extractor._model,
            max_tokens=20,
            messages=[{"role": "user", "content": prompt}],
        )
        if msg.content:
            return msg.content[0].text or ""
        return ""
    if cls_name == "OpenAIExtractor":
        resp = ai_extractor._client.chat.completions.create(
            model=ai_extractor._model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20, temperature=0,
        )
        return resp.choices[0].message.content or ""
    if cls_name == "GeminiExtractor":
        return ai_extractor._generate(prompt) or ""
    logger.warning("Clasificador IA: proveedor desconocido '%s'", cls_name)
    return ""


def classify_with_ai(
    file_name: str,
    text_sample: str,
    ai_extractor,
    max_sample_chars: int = 4000,
) -> ClassificationResult | None:
    """Clasifica vía IA. Devuelve None si la IA falla o responde algo inválido."""
    if not text_sample or not ai_extractor:
        return None
    extracto = text_sample.strip()[:max_sample_chars]
    if not extracto:
        return None

    tipos_str = "\n".join(f"- {r}" for r in _ROLES_IA)
    prompt = _PROMPT_CLASIFICADOR.format(
        filename=file_name, tipos=tipos_str, extracto=extracto,
    )

    try:
        respuesta = _invoke_ai_short(ai_extractor, prompt)
    except Exception as e:
        logger.warning("Clasificador IA falló para %s: %s", file_name, e)
        return None

    if not respuesta:
        return None

    # Normalizar respuesta: primera línea, solo letras y guiones bajos
    rol = respuesta.strip().lower().splitlines()[0].strip()
    rol = re.sub(r"[^a-z_]", "", rol)
    if rol not in _ROLES_IA:
        logger.info("IA devolvió rol no válido para %s: '%s'", file_name, respuesta[:60])
        return None

    return ClassificationResult(
        rol=rol, fuente="ia_inicio", confianza=CONFIANZA["ia_inicio"],
        notas=f"IA clasificó como '{rol}'",
    )


# ── Punto de entrada ──────────────────────────────────────────────────────────

def classify_file(
    file_name: str,
    subfolder: str | None = None,
    text_sample: str | None = None,
    ai_extractor=None,
) -> ClassificationResult:
    """
    Cascada completa. Siempre devuelve un ClassificationResult — nunca None.

    Orden:
      1. Heurística (extensión/carpeta/nombre fuerte) — si confianza >= 0.8 se devuelve directo.
      2. IA corta si se proporciona text_sample + ai_extractor.
      3. Heurística débil si quedó por ahí.
      4. Fallback 'otro' confianza 0.
    """
    heuristic = classify_heuristic(file_name, subfolder)
    if heuristic and heuristic.confianza >= CONFIANZA["heuristica_nombre"]:
        return heuristic

    weak = heuristic  # podría ser una coincidencia débil que vale como respaldo

    if text_sample and ai_extractor:
        ai_result = classify_with_ai(file_name, text_sample, ai_extractor)
        if ai_result:
            return ai_result

    if weak:
        return weak

    return ClassificationResult(
        rol="otro", fuente="fallback_otro", confianza=CONFIANZA["fallback_otro"],
        notas="Sin patrón ni IA pudieron clasificar el archivo",
    )
