"""
Excel como tabla estructurada (Sprint Drive D).

Cuando un archivo Excel/CSV tiene encabezados reconocibles (nombre, cédula,
edad, parentesco, …), se procesa SIN IA: pandas lee la tabla, un mapper
asocia columnas crudas → campos del esquema del Sprint B, y se generan los
agregados (total personas, distribución por edad/sexo, etc.).

Soporta hoy:
  - autocenso / autocenso_depurado / censo_comunidad: filas = personas
  - registro_asistencia: filas = asistentes

Otros tipos en Excel caen al flujo normal de texto + IA.
"""
from __future__ import annotations

import logging
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


# Sinónimos de encabezados (todos normalizados: lowercase, sin acentos/espacios)
COLUMN_SYNONYMS: dict[str, list[str]] = {
    "nombre":          ["nombre", "nombres", "nombrecompleto", "apellidosynombres", "nombreapellido", "apellidosnombres"],
    "cedula":          ["cedula", "documento", "numerodocumento", "cc", "identificacion", "noidentificacion", "documentoidentidad", "numerocedula"],
    "edad":            ["edad", "edadanios", "edadenanos", "edadaproximada"],
    "fecha_nacimiento": ["fechanacimiento", "fechadenacimiento", "nacimiento", "fnac", "fechanac"],
    "sexo":            ["sexo", "genero", "sex"],
    "parentesco":      ["parentesco", "relacionjefehogar", "relacionjefe", "relacionjefedehogar", "relacion"],
    "rol_comunidad":   ["rolcomunidad", "rol", "cargo", "funcioncomunidad", "funcion", "ocupacion"],
    "firma":           ["firma", "firmo", "asistio"],
    "familia":         ["familia", "idfamilia", "numerofamilia", "hogar", "nucleofamiliar", "nucleo"],
    "telefono":        ["telefono", "celular", "tel", "movil", "contacto"],
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _norm_header(h: Any) -> str:
    s = str(h or "")
    nfkd = unicodedata.normalize("NFKD", s)
    sin = "".join(c for c in nfkd if not unicodedata.combining(c))
    return sin.lower().replace(" ", "").replace("_", "").replace(".", "").replace("-", "")


def _safe_str(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, float) and pd.isna(v):
        return None
    s = str(v).strip()
    return s or None


def _safe_int(v: Any) -> int | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return None


# ── Lectura de Excel ──────────────────────────────────────────────────────────

def parse_excel(path: str | Path) -> dict[str, Any]:
    """
    Lee el Excel y devuelve:
      { "sheets": [{ "name": str, "headers_raw": [...], "rows": [{col: val, ...}] }] }

    Se intentan varias filas iniciales como encabezado si la primera fila parece tener
    pocos campos no-nulos (formato común: título en fila 1, encabezados en fila 2 o 3).
    """
    try:
        xl = pd.ExcelFile(path)
    except Exception as e:
        logger.warning("No se pudo abrir Excel %s: %s", path, e)
        return {"sheets": []}

    sheets: list[dict[str, Any]] = []
    for name in xl.sheet_names:
        try:
            df_raw = xl.parse(name, dtype=object, header=None)
        except Exception as e:
            logger.warning("Hoja '%s' falló: %s", name, e)
            continue
        if df_raw.empty:
            continue

        # Intentar las primeras 5 filas como cabecera; quedarse con la que dé más matches.
        best_header_row = 0
        best_match_count = -1
        best_df: pd.DataFrame | None = None
        for hr in range(min(5, len(df_raw))):
            try:
                df_try = xl.parse(name, dtype=object, header=hr)
            except Exception:
                continue
            df_try = df_try.dropna(how="all").dropna(axis=1, how="all")
            if df_try.empty:
                continue
            normalized = {_norm_header(c) for c in df_try.columns}
            matches = sum(
                1 for syns in COLUMN_SYNONYMS.values()
                if any(s in normalized for s in syns)
            )
            if matches > best_match_count:
                best_match_count = matches
                best_header_row = hr
                best_df = df_try

        if best_df is None or best_df.empty:
            continue

        sheets.append({
            "name": name,
            "headers_raw": [str(c) for c in best_df.columns],
            "rows": best_df.to_dict(orient="records"),
            "header_row_index": best_header_row,
            "match_count": best_match_count,
        })

    return {"sheets": sheets}


def detect_table_columns(headers_raw: list[str]) -> dict[str, str]:
    """
    Para cada campo canónico, encuentra la primera columna del Excel cuyo
    encabezado normalizado coincide con alguno de sus sinónimos.

    Returns: {field_canonico: header_original}
    """
    normalized_to_raw = {_norm_header(h): h for h in headers_raw}
    mapping: dict[str, str] = {}
    for field, syns in COLUMN_SYNONYMS.items():
        for norm, raw in normalized_to_raw.items():
            if any(syn == norm or (len(syn) >= 5 and syn in norm) for syn in syns):
                mapping[field] = raw
                break
    return mapping


# ── Parsers por rol ───────────────────────────────────────────────────────────

def excel_to_autocenso(path: str | Path) -> dict | None:
    """Parsea un Excel como tabla de personas. None si no luce tabular reconocible."""
    parsed = parse_excel(path)
    if not parsed["sheets"]:
        return None

    main_sheet = max(parsed["sheets"], key=lambda s: (s.get("match_count", 0), len(s["rows"])))
    mapping = detect_table_columns(main_sheet["headers_raw"])

    if "nombre" not in mapping:
        return None  # Sin columna de nombre, no es una lista de personas

    personas: list[dict] = []
    familias: set[str] = set()
    for row in main_sheet["rows"]:
        nombre = _safe_str(row.get(mapping["nombre"]))
        if not nombre:
            continue
        p: dict[str, Any] = {"nombre": nombre}
        if "cedula" in mapping:        p["cedula"]          = _safe_str(row.get(mapping["cedula"]))
        if "edad" in mapping:          p["edad"]            = _safe_int(row.get(mapping["edad"]))
        if "sexo" in mapping:          p["sexo"]            = _safe_str(row.get(mapping["sexo"]))
        if "parentesco" in mapping:    p["parentesco"]      = _safe_str(row.get(mapping["parentesco"]))
        if "rol_comunidad" in mapping: p["rol_comunidad"]   = _safe_str(row.get(mapping["rol_comunidad"]))
        if "familia" in mapping:       p["familia"]         = _safe_str(row.get(mapping["familia"]))

        # Identificar familias por columna explícita o por jefes de hogar
        if p.get("familia"):
            familias.add(p["familia"])
        elif (p.get("parentesco") or "").lower().startswith("jefe"):
            familias.add(nombre)

        personas.append(p)

    if not personas:
        return None

    # Distribución por sexo
    sexo_counter = {"femenino": 0, "masculino": 0, "otro": 0}
    for p in personas:
        s = (p.get("sexo") or "").lower()
        if s.startswith("f") or s in ("femenino", "mujer"):
            sexo_counter["femenino"] += 1
        elif s.startswith("m") or s in ("masculino", "hombre", "varon"):
            sexo_counter["masculino"] += 1
        elif s:
            sexo_counter["otro"] += 1

    # Distribución por edad en rangos estándar
    rangos = {"0-5": 0, "6-17": 0, "18-60": 0, "60+": 0}
    edad_count = 0
    for p in personas:
        e = p.get("edad")
        if e is None:
            continue
        edad_count += 1
        if e <= 5:        rangos["0-5"] += 1
        elif e <= 17:     rangos["6-17"] += 1
        elif e <= 60:     rangos["18-60"] += 1
        else:             rangos["60+"] += 1

    distribucion_edad = [{"rango": r, "cantidad": c} for r, c in rangos.items() if c > 0]

    # Jefes de hogar
    jefes: list[dict] = []
    for p in personas:
        if (p.get("parentesco") or "").lower().startswith("jefe"):
            jefes.append({
                "nombre": p.get("nombre"),
                "edad": p.get("edad"),
                "rol_comunidad": p.get("rol_comunidad"),
                "cedula": p.get("cedula"),
            })

    return {
        "fecha_registro": None,
        "total_personas": len(personas),
        "total_familias": len(familias) if familias else None,
        "coordinador_registro": None,
        "distribucion_por_edad": distribucion_edad if edad_count else [],
        "distribucion_por_sexo": sexo_counter if any(sexo_counter.values()) else {"femenino": None, "masculino": None, "otro": None},
        "jefes_de_hogar": jefes,
        "discrepancia_con_censo_general": None,
        "extra": {
            "fuente_excel": Path(path).name,
            "hoja_principal": main_sheet["name"],
            "filas_procesadas": len(personas),
            "hojas_disponibles": [s["name"] for s in parsed["sheets"]],
            "columnas_mapeadas": mapping,
            "personas_completas": personas,   # tabla completa por si Sprint E la necesita
        },
    }


def excel_to_registro_asistencia(path: str | Path) -> dict | None:
    parsed = parse_excel(path)
    if not parsed["sheets"]:
        return None

    main_sheet = max(parsed["sheets"], key=lambda s: (s.get("match_count", 0), len(s["rows"])))
    mapping = detect_table_columns(main_sheet["headers_raw"])

    if "nombre" not in mapping:
        return None

    asistentes: list[dict] = []
    for row in main_sheet["rows"]:
        nombre = _safe_str(row.get(mapping["nombre"]))
        if not nombre:
            continue
        a: dict[str, Any] = {"nombre": nombre}
        if "cedula" in mapping:        a["cedula"] = _safe_str(row.get(mapping["cedula"]))
        if "rol_comunidad" in mapping: a["cargo"]  = _safe_str(row.get(mapping["rol_comunidad"]))
        if "firma" in mapping:         a["firma"]  = _safe_str(row.get(mapping["firma"]))
        asistentes.append(a)

    if not asistentes:
        return None

    return {
        "fecha_evento": None,
        "lugar_evento": None,
        "tipo_evento": None,
        "asistentes": asistentes,
        "total_asistentes": len(asistentes),
        "extra": {
            "fuente_excel": Path(path).name,
            "hoja_principal": main_sheet["name"],
            "columnas_mapeadas": mapping,
        },
    }


# ── Dispatcher ────────────────────────────────────────────────────────────────

def parse_excel_for_role(path: str | Path, rol: str | None) -> dict | None:
    """
    Punto de entrada: si el archivo es Excel y el rol es soportado por tabla,
    devuelve un JSON estructurado listo para guardar (sin pasar por IA).
    None si no aplica → el caller debe caer al flujo IA.
    """
    p = Path(path)
    if p.suffix.lower() not in (".xlsx", ".xls"):
        return None
    if rol in ("autocenso", "autocenso_depurado", "censo_comunidad"):
        return excel_to_autocenso(p)
    if rol == "registro_asistencia":
        return excel_to_registro_asistencia(p)
    return None


def is_tabular_excel(path: str | Path) -> bool:
    """Helper para detectar si un Excel parece tabular reconocible."""
    p = Path(path)
    if p.suffix.lower() not in (".xlsx", ".xls"):
        return False
    parsed = parse_excel(p)
    if not parsed["sheets"]:
        return False
    main = max(parsed["sheets"], key=lambda s: s.get("match_count", 0))
    return main.get("match_count", 0) >= 2  # ≥2 columnas reconocidas = tabular
