"""
Utilidades para parsear coordenadas geográficas desde texto extraído por la IA.

Formatos soportados:
  - Decimal:   "Maloka|1.3744|-75.4000"    (formato pipe del extractor)
  - DMS:       "1°22′28″N 75°24′00″W"
  - Plus Code: "9J72+5V Milán"             (requiere openlocationcode)
  - Nominal:   geocodificación por nombre  (requiere red, opcional)
"""
from __future__ import annotations

import logging
import re
from typing import NamedTuple

logger = logging.getLogger(__name__)

# Bounding box aproximado de Colombia (holgura extra para territorios ancestrales)
_LAT_MIN, _LAT_MAX = -5.0, 14.0
_LNG_MIN, _LNG_MAX = -82.0, -66.0


class Coord(NamedTuple):
    lat: float
    lng: float


def _in_colombia(lat: float, lng: float) -> bool:
    return _LAT_MIN <= lat <= _LAT_MAX and _LNG_MIN <= lng <= _LNG_MAX


# ── Formato pipe del extractor IA: "NombreSitio|lat|lng" ─────────────────────

def parse_pipe_format(valor: str) -> tuple[str, Coord] | None:
    """
    Parsea el formato que la IA produce para coordenada_gps:
    "NombreSitio|lat_decimal|lng_decimal"
    """
    parts = [p.strip() for p in valor.split("|")]
    if len(parts) < 3:
        return None
    nombre = parts[0] or "Punto extraído"
    try:
        lat = float(parts[1].replace(",", "."))
        lng = float(parts[2].replace(",", "."))
    except ValueError:
        return None
    if not _in_colombia(lat, lng):
        return None
    return nombre, Coord(lat, lng)


# ── Grados-Minutos-Segundos ───────────────────────────────────────────────────

_DMS_RE = re.compile(
    r"""
    (\d+)\s*[°º]\s*(\d+)\s*[′']\s*([\d.]+)\s*[″"]\s*([NSns])
    [\s,;]*
    (\d+)\s*[°º]\s*(\d+)\s*[′']\s*([\d.]+)\s*[″"]\s*([EWew])
    """,
    re.VERBOSE | re.UNICODE,
)


def parse_dms(text: str) -> Coord | None:
    m = _DMS_RE.search(text)
    if not m:
        return None
    d1, m1, s1, dir1, d2, m2, s2, dir2 = m.groups()
    lat = float(d1) + float(m1) / 60 + float(s1) / 3600
    lng = float(d2) + float(m2) / 60 + float(s2) / 3600
    if dir1.upper() == "S":
        lat = -lat
    if dir2.upper() == "W":
        lng = -lng
    if not _in_colombia(lat, lng):
        return None
    return Coord(lat, lng)


# ── Decimal puro ──────────────────────────────────────────────────────────────

_DECIMAL_RE = re.compile(
    r"(-?\d{1,2}\.?\d{0,7})\s*[,;]\s*(-?\d{2,3}\.?\d{0,7})"
)


def parse_decimal(text: str) -> Coord | None:
    for m in _DECIMAL_RE.finditer(text):
        try:
            lat, lng = float(m.group(1)), float(m.group(2))
            if _in_colombia(lat, lng):
                return Coord(lat, lng)
        except ValueError:
            continue
    return None


# ── Plus Code (Google Open Location Code) ────────────────────────────────────

# Referencia centroide Caquetá para resolver short codes
_CAQUETA_LAT, _CAQUETA_LNG = 1.0, -74.5


def parse_plus_code(code: str, ref_lat: float = _CAQUETA_LAT, ref_lng: float = _CAQUETA_LNG) -> Coord | None:
    try:
        from openlocationcode.openlocationcode import decode, isFull, isShort, recoverNearest
        code_clean = code.strip().split()[0]  # tomar solo el código, sin el municipio
        if isShort(code_clean):
            code_clean = recoverNearest(code_clean, ref_lat, ref_lng)
        if isFull(code_clean):
            area = decode(code_clean)
            lat = (area.latitudeLo + area.latitudeHi) / 2
            lng = (area.longitudeLo + area.longitudeHi) / 2
            if _in_colombia(lat, lng):
                return Coord(lat, lng)
    except ImportError:
        logger.debug("openlocationcode no instalado — Plus Code omitido")
    except Exception as e:
        logger.warning("Error parseando Plus Code '%s': %s", code, e)
    return None


# ── Geocodificación por nombre (Nominatim, opcional) ─────────────────────────

def geocode_name(nombre: str, timeout: float = 3.0) -> Coord | None:
    """
    Intenta geocodificar un nombre de lugar usando Nominatim (OpenStreetMap).
    Requiere conexión a internet. Devuelve None si falla.
    """
    try:
        import httpx
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": f"{nombre}, Colombia",
            "format": "json",
            "limit": 1,
            "countrycodes": "co",
        }
        headers = {"User-Agent": "EtnoSIG-Cabildo/1.0"}
        resp = httpx.get(url, params=params, headers=headers, timeout=timeout)
        data = resp.json()
        if data:
            lat = float(data[0]["lat"])
            lng = float(data[0]["lon"])
            if _in_colombia(lat, lng):
                return Coord(lat, lng)
    except Exception as e:
        logger.debug("Geocodificación de '%s' falló: %s", nombre, e)
    return None


# ── Dispatcher principal ──────────────────────────────────────────────────────

_TIPO_MAP = {
    "maloka":      "sede_cabildo",
    "cabildo":     "sede_cabildo",
    "sede":        "sede_cabildo",
    "sagrado":     "sitio_sagrado",
    "espiritual":  "sitio_sagrado",
    "ceremonial":  "sitio_sagrado",
    "resguardo":   "territorio_ancestral",
    "territorio":  "territorio_ancestral",
    "origen":      "lugar_historico",
    "histórico":   "lugar_historico",
    "historico":   "lugar_historico",
    "migr":        "ruta_migratoria",
    "río":         "punto_geografico",
    "rio":         "punto_geografico",
    "quebrada":    "punto_geografico",
    "vereda":      "punto_geografico",
    "municipio":   "punto_geografico",
}


def infer_tipo(nombre: str, descripcion: str = "") -> str:
    texto = (nombre + " " + descripcion).lower()
    for kw, tipo in _TIPO_MAP.items():
        if kw in texto:
            return tipo
    return "punto_geografico"


def parse_extraction_to_location(tipo_dato: str, valor: str, fuente: str | None = None) -> dict | None:
    """
    Convierte una CorpusExtraction de tipo coordenada en un dict listo para StudyLocation.
    Retorna None si no se puede parsear.
    """
    coord: Coord | None = None
    nombre = "Punto extraído"
    descripcion = valor[:300]

    if tipo_dato == "coordenada_gps":
        parsed = parse_pipe_format(valor)
        if parsed:
            nombre, coord = parsed
        else:
            coord = parse_dms(valor) or parse_decimal(valor)

    elif tipo_dato == "plus_code":
        coord = parse_plus_code(valor)
        nombre = f"Plus Code {valor.strip().split()[0]}"

    elif tipo_dato == "sitio_geografico":
        # Formato: "NombreSitio|descripcion"
        parts = [p.strip() for p in valor.split("|", 1)]
        nombre = parts[0] if parts else valor[:100]
        if len(parts) > 1:
            descripcion = parts[1]
        # Intentar geocodificar por nombre
        coord = geocode_name(nombre)

    if coord is None:
        return None

    return {
        "nombre": nombre[:300],
        "tipo": infer_tipo(nombre, descripcion),
        "lat": float(coord.lat),
        "lng": float(coord.lng),
        "descripcion": descripcion or None,
        "fuente_archivo": fuente,
        "confianza": 0.85,
    }
