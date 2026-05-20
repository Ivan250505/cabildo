"""
Extractor para fotos (Sprint Drive D).

Cascada:
  1. EXIF GPS (sin IA). Si la foto tiene lat/lng, crear StudyLocation directo.
  2. Si el rol es evidencia_foto, Vision corta: contenido, texto visible, coordenadas.

Si no es evidencia_foto y no tiene EXIF GPS, la foto no produce datos
estructurados (no se pasa por IA larga).
"""
from __future__ import annotations

import io
import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ── EXIF GPS ──────────────────────────────────────────────────────────────────

def _dms_to_decimal(dms: Any, ref: str | None) -> float | None:
    """Convierte coordenada EXIF (degrees, minutes, seconds) + ref (N/S/E/W) a decimal."""
    if dms is None or ref is None:
        return None
    try:
        # En Pillow modernos viene como tuple de tres Rational/IFDRational
        d = float(dms[0])
        m = float(dms[1])
        s = float(dms[2])
        decimal = d + m / 60 + s / 3600
        if str(ref).upper() in ("S", "W"):
            decimal = -decimal
        return round(decimal, 7)
    except (TypeError, ValueError, IndexError) as e:
        logger.debug("DMS inválido (%s, ref=%s): %s", dms, ref, e)
        return None


def extract_exif_gps(path: str | Path) -> dict | None:
    """
    Lee EXIF GPS de una imagen. Devuelve {lat, lng, altitude?} o None.
    """
    try:
        from PIL import Image, ExifTags
    except ImportError:
        logger.warning("Pillow no instalado — no se puede leer EXIF")
        return None

    p = Path(path)
    if not p.exists():
        return None

    try:
        img = Image.open(p)
        exif = img.getexif() if hasattr(img, "getexif") else None
        if not exif:
            return None
    except Exception as e:
        logger.debug("No se pudo abrir EXIF de %s: %s", p, e)
        return None

    # Buscar GPSInfo (tag 34853)
    gps_ifd = exif.get_ifd(0x8825) if hasattr(exif, "get_ifd") else None
    if not gps_ifd:
        return None

    gps_data: dict[str, Any] = {
        ExifTags.GPSTAGS.get(k, k): v for k, v in gps_ifd.items()
    }
    lat = _dms_to_decimal(gps_data.get("GPSLatitude"), gps_data.get("GPSLatitudeRef"))
    lng = _dms_to_decimal(gps_data.get("GPSLongitude"), gps_data.get("GPSLongitudeRef"))

    if lat is None or lng is None:
        return None
    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        return None

    result: dict[str, Any] = {"lat": lat, "lng": lng}
    altitude = gps_data.get("GPSAltitude")
    if altitude:
        try:
            result["altitude_m"] = round(float(altitude), 2)
        except (ValueError, TypeError):
            pass
    return result


# ── Vision corta para descripción de foto ─────────────────────────────────────

_PROMPT_PHOTO = """Mira esta foto del corpus de un estudio etnológico colombiano.

Responde EXACTAMENTE este JSON (sin texto antes/después, sin bloques de código):

{
  "contenido": "paisaje|retrato|documento|mapa|grupo|objeto|otro",
  "descripcion": "una sola frase corta describiendo lo que muestra",
  "tiene_texto_visible": true|false,
  "texto_visible": "el texto si lo hay, o null",
  "coordenadas_visibles": "lat,lng si aparecen en un cartel/GPS visible, o null"
}

Si no estás seguro de algún campo, usa null. NO inventes.
"""


def describe_photo_via_vision(
    path: str | Path,
    api_key: str,
    model_name: str = "gemini-2.0-flash-lite",
) -> dict | None:
    """Llama a Vision para clasificar el contenido de una foto. None si falla."""
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        logger.info("google-genai no instalado — no se puede Vision por foto")
        return None

    p = Path(path)
    if not p.exists():
        return None

    ext = p.suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".webp": "image/webp", ".heic": "image/heic",
    }
    mime = mime_map.get(ext, "image/jpeg")

    try:
        raw_bytes = p.read_bytes()
    except Exception as e:
        logger.warning("No se pudo leer foto %s: %s", p, e)
        return None

    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=[
                types.Part.from_bytes(data=raw_bytes, mime_type=mime),
                _PROMPT_PHOTO,
            ],
        )
        raw = (response.text or "").strip()
    except Exception as e:
        logger.warning("Vision falló para %s: %s", p, e)
        return None

    # Parsear el JSON (tolerante a ```json fences)
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group())
    except json.JSONDecodeError as e:
        logger.warning("JSON inválido en Vision para %s: %s", p, e)
        return None


# ── Punto de entrada ──────────────────────────────────────────────────────────

def extract_photo_data(
    path: str | Path,
    rol: str | None,
    gemini_api_key: str | None = None,
    gemini_model: str = "gemini-2.0-flash-lite",
) -> tuple[dict | None, str]:
    """
    Procesa una foto.

    Returns:
        (datos_estructurados, metodo_extraccion)
        metodo_extraccion ∈ {"exif_gps", "vision_imagen_completa", "exif_gps_y_vision",
                              "no_procesable"}
    """
    p = Path(path)
    if p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".heic", ".webp"):
        return None, "no_procesable"

    gps = extract_exif_gps(p)
    descripcion: dict | None = None

    # Solo invertimos tokens en Vision si el rol es evidencia_foto
    if rol == "evidencia_foto" and gemini_api_key:
        descripcion = describe_photo_via_vision(p, gemini_api_key, gemini_model)

    if gps is None and descripcion is None:
        return None, "no_procesable"

    datos: dict[str, Any] = {
        "archivo": p.name,
        "coordenadas_exif": gps,
        "descripcion_vision": descripcion,
        "ubicacion_sugerida": None,
        "extra": {},
    }

    # Construir ubicación sugerida para StudyLocation
    if gps:
        datos["ubicacion_sugerida"] = {
            "nombre": p.stem,
            "tipo": "punto_geografico",
            "lat": gps["lat"],
            "lng": gps["lng"],
            "descripcion": (descripcion or {}).get("descripcion") if descripcion else None,
            "fuente": "exif_gps",
        }

    if gps and descripcion:
        metodo = "exif_gps_y_vision"
    elif gps:
        metodo = "exif_gps"
    else:
        metodo = "vision_imagen_completa"

    return datos, metodo
