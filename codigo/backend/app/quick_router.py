"""Endpoint sencillo: sube un archivo, IA genera resumen."""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.auth.models import User
from app.auth.service import get_current_user
from app.config import get_settings
from app.documents.ai_extractor import get_ai_extractor
from app.documents.extractor import (
    extract_text_docx,
    extract_text_excel,
    extract_text_pdf,
)

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/quick", tags=["quick"])

_MAX_BYTES = 20 * 1024 * 1024  # 20 MB
_TEXT_EXTS = {".txt", ".md", ".csv"}


def _read_text(path: Path, suffix: str) -> str:
    if suffix == ".pdf":
        return extract_text_pdf(path)
    if suffix == ".docx":
        return extract_text_docx(path)
    if suffix in {".xlsx", ".xls"}:
        return extract_text_excel(path)
    if suffix in _TEXT_EXTS:
        return path.read_text(encoding="utf-8", errors="ignore")
    raise HTTPException(status_code=415, detail=f"Extensión no soportada: {suffix}")


@router.post("/summarize")
async def summarize_file(
    file: UploadFile = File(...),
    _: User = Depends(get_current_user),
):
    """Recibe un archivo, extrae su texto y devuelve un resumen generado por IA."""
    if settings.AI_PROVIDER.lower() == "none" or not settings.AI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="La IA no está configurada en el servidor (AI_PROVIDER=none)",
        )

    filename = file.filename or "archivo"
    suffix = Path(filename).suffix.lower()

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="El archivo está vacío")
    if len(content) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="El archivo supera los 20 MB")

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        text = _read_text(tmp_path, suffix)
    finally:
        tmp_path.unlink(missing_ok=True)

    text = (text or "").strip()
    if not text:
        raise HTTPException(
            status_code=422,
            detail="No se pudo extraer texto del archivo (¿escaneado sin OCR?)",
        )

    extractor = get_ai_extractor(
        provider=settings.AI_PROVIDER,
        api_key=settings.AI_API_KEY,
        model=settings.AI_MODEL,
    )
    if not extractor:
        raise HTTPException(status_code=503, detail="No se pudo inicializar la IA")

    try:
        resumen = extractor.summarize(text, filename)
    except Exception as e:
        msg = str(e).lower()
        if "429" in msg or "quota" in msg or "rate" in msg:
            raise HTTPException(
                status_code=429,
                detail="Cuota de la IA agotada (429). Espera 1-2 minutos o cambia de modelo/key.",
            ) from e
        if "404" in msg or "not found" in msg:
            real_model = getattr(extractor, "model_name", None) or settings.AI_MODEL or "(default)"
            alternativas = [m for m in (
                "gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-2.5-flash", "gemini-1.5-flash",
            ) if m != real_model]
            raise HTTPException(
                status_code=502,
                detail=(
                    f"Modelo '{real_model}' no encontrado o sin acceso para esta API key. "
                    f"Prueba cambiando AI_MODEL en .env a uno de: {', '.join(alternativas)}."
                ),
            ) from e
        if "permission" in msg or "auth" in msg or "401" in msg or "403" in msg:
            raise HTTPException(
                status_code=502,
                detail="API key de IA inválida o sin permisos.",
            ) from e
        logger.exception("Error inesperado de la IA")
        raise HTTPException(status_code=502, detail=f"Error de la IA: {str(e)[:200]}") from e

    if not resumen:
        raise HTTPException(status_code=502, detail="La IA no devolvió respuesta")

    return {
        "archivo": filename,
        "tamano_bytes": len(content),
        "texto_chars": len(text),
        "resumen": resumen,
    }


@router.get("/ai-models")
async def list_ai_models(_: User = Depends(get_current_user)):
    """
    Lista los modelos IA disponibles para la API key configurada. Útil para
    depurar errores 'modelo no encontrado': muestra el ID exacto que acepta
    el proveedor (ej. 'models/gemini-2.0-flash-lite-001').
    """
    provider = settings.AI_PROVIDER.lower()
    if provider == "none" or not settings.AI_API_KEY:
        raise HTTPException(status_code=503, detail="AI_PROVIDER no configurado")

    if provider != "gemini":
        raise HTTPException(
            status_code=501,
            detail=f"Listado solo implementado para gemini (proveedor actual: {provider})",
        )

    # Usamos REST directo de Google AI Studio (Generative Language API) porque
    # el SDK google-genai 0.7.0 expone models.list() solo contra Vertex AI.
    import httpx
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={settings.AI_API_KEY}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as http:
            resp = await http.get(url)
    except Exception as e:
        logger.exception("Error de red listando modelos")
        raise HTTPException(status_code=502, detail=f"Error de red contra Google: {str(e)[:300]}") from e

    if resp.status_code == 401 or resp.status_code == 403:
        raise HTTPException(
            status_code=502,
            detail=f"API key inválida o sin permisos (HTTP {resp.status_code}). Verifica AI_API_KEY en .env.",
        )
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"Google respondió HTTP {resp.status_code}: {resp.text[:400]}",
        )

    data = resp.json()
    raw_models = data.get("models", [])

    modelos: list[dict] = []
    for m in raw_models:
        name = m.get("name", "") or ""
        short = name.removeprefix("models/")
        supported = m.get("supportedGenerationMethods", []) or []
        modelos.append({
            "id_api": short,
            "id_completo": name,
            "display_name": m.get("displayName"),
            "version": m.get("version"),
            "input_token_limit": m.get("inputTokenLimit"),
            "output_token_limit": m.get("outputTokenLimit"),
            "soporta_generate": "generateContent" in supported,
            "metodos_soportados": supported,
        })

    modelos.sort(key=lambda x: (
        0 if "flash-lite" in (x["id_api"] or "") else
        1 if "flash" in (x["id_api"] or "") else
        2 if "pro" in (x["id_api"] or "") else 3,
        x["id_api"] or "",
    ))

    return {
        "provider": "gemini",
        "modelo_configurado": settings.AI_MODEL,
        "total": len(modelos),
        "modelos": modelos,
    }
