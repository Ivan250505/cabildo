"""
Google Drive integration service.

OAuth2 flow:
  1. generate_auth_url()  → redirect user to Google consent screen
  2. exchange_code()      → exchange auth code for tokens, encrypt and store in DB
  3. build_drive_client() → reconstruct authenticated Drive API client from stored tokens

Sync flow:
  sync_study() → for each phase URL in the study, list Drive folder files,
                 download new/updated files, create StudyCorpus records.
"""
from __future__ import annotations

import io
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from jose import jwt as jose_jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.config import get_settings
from app.drive.crypto import decrypt_token, encrypt_token
from app.drive.schemas import DriveFileInfo, FolderListResponse, SyncResult, StudySyncResponse, FolderFilesResponse, FolderFileItem
from app.studies.models import CorpusExtraction, Study, StudyCorpus

settings = get_settings()

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file",
]

# ── Tipos de archivo soportados (MIME → corpus tipo) ──────────────────────────

_MIME_TO_TIPO: dict[str, str] = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.google-apps.document": "docx",   # exportar como docx
    "application/vnd.google-apps.spreadsheet": "xlsx",  # exportar como xlsx
    "image/jpeg": "jpg",
    "image/heic": "heic",
    "video/mp4": "mp4",
    "audio/mpeg": "mp3",
    "application/zip": "otro",
    "application/octet-stream": "otro",
}

# Extensión de archivo → tipo de corpus (fallback cuando el MIME no está mapeado)
_EXT_TO_TIPO: dict[str, str] = {
    ".pdf": "pdf",
    ".docx": "docx", ".doc": "docx",
    ".xlsx": "xlsx", ".xls": "xlsx",
    ".qgz": "qgz", ".qgs": "qgz",
    ".gpkg": "gpkg",
    ".shp": "shp", ".dbf": "shp", ".prj": "shp", ".shx": "shp",
    ".jpg": "jpg", ".jpeg": "jpg", ".png": "jpg",
    ".heic": "heic",
    ".mp4": "mp4", ".mov": "mp4",
    ".mp3": "mp3", ".m4a": "mp3",
}


def _get_tipo(mime: str, filename: str) -> str:
    """Resolve corpus tipo from MIME type, with file-extension fallback."""
    tipo = _MIME_TO_TIPO.get(mime)
    if tipo and tipo != "otro":
        return tipo
    ext = Path(filename).suffix.lower()
    return _EXT_TO_TIPO.get(ext, "otro")


# MIME de exportación para Google Docs nativos
_GOOGLE_EXPORT_MIME: dict[str, str] = {
    "application/vnd.google-apps.document": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ),
    "application/vnd.google-apps.spreadsheet": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ),
}

# Extensiones para documentos exportados
_EXPORT_EXT: dict[str, str] = {
    "application/vnd.google-apps.document": ".docx",
    "application/vnd.google-apps.spreadsheet": ".xlsx",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _client_config() -> dict:
    return {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
        }
    }


def _extract_folder_id(url: str) -> str | None:
    """Extract the Drive folder ID from a Google Drive URL."""
    match = re.search(r"/folders/([a-zA-Z0-9_-]{10,})", url)
    return match.group(1) if match else None


_FOLDER_MIME = "application/vnd.google-apps.folder"


def _list_folder_recursive(
    service, folder_id: str, rel_path: str = ""
) -> list[tuple[dict, str]]:
    """Recursively list all downloadable files inside a Drive folder.

    Returns a flat list of (file_metadata, relative_subfolder_path) tuples.
    Subfolders are traversed but not included in the result.
    """
    query = f"'{folder_id}' in parents and trashed = false"
    fields = "files(id,name,mimeType,size,modifiedTime)"
    result = service.files().list(q=query, fields=fields, pageSize=500).execute()
    items = result.get("files", [])

    files: list[tuple[dict, str]] = []
    for item in items:
        if item["mimeType"] == _FOLDER_MIME:
            child_rel = f"{rel_path}/{item['name']}" if rel_path else item["name"]
            files.extend(_list_folder_recursive(service, item["id"], child_rel))
        else:
            files.append((item, rel_path))
    return files


def _get_user_or_raise(user: User) -> dict:
    if not user.google_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No hay cuenta de Google conectada. Use /api/drive/auth-url primero.",
        )
    return decrypt_token(user.google_token)


# ── OAuth2 ────────────────────────────────────────────────────────────────────

def generate_auth_url(user_id: str) -> tuple[str, str]:
    """Return (authorization_url, state) with user_id encoded in the state JWT."""
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES)
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    # Encode user_id in state so the callback can identify the user without JWT header
    state = jose_jwt.encode(
        {"sub": user_id, "type": "drive_oauth"},
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    return url, state


def decode_oauth_state(state: str) -> str:
    """Decode the state JWT and return the user_id (str)."""
    try:
        payload = jose_jwt.decode(state, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != "drive_oauth":
            raise ValueError("tipo incorrecto")
        return payload["sub"]
    except (JWTError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Estado OAuth inválido: {exc}")


async def exchange_code(db: AsyncSession, user: User, code: str) -> None:
    """Exchange the OAuth2 authorization code for tokens and store encrypted in DB."""
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES)
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    flow.fetch_token(code=code)

    creds = flow.credentials
    token_dict = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes or SCOPES),
    }
    user.google_token = encrypt_token(token_dict)
    await db.flush()


async def revoke_token(db: AsyncSession, user: User) -> None:
    """Remove stored Google token from the user record."""
    user.google_token = None
    await db.flush()


# ── Drive client ──────────────────────────────────────────────────────────────

def build_drive_client(user: User):
    """Build an authenticated Drive API client, refreshing the token if needed."""
    token_dict = _get_user_or_raise(user)
    creds = Credentials(
        token=token_dict["token"],
        refresh_token=token_dict.get("refresh_token"),
        token_uri=token_dict.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token_dict.get("client_id", settings.GOOGLE_CLIENT_ID),
        client_secret=token_dict.get("client_secret", settings.GOOGLE_CLIENT_SECRET),
        scopes=token_dict.get("scopes", SCOPES),
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def get_drive_user_info(user: User) -> dict | None:
    """Return basic info about the connected Google account."""
    try:
        service = build_drive_client(user)
        info = service.about().get(fields="user").execute()
        return info.get("user", {})
    except Exception:
        return None


# ── File listing ──────────────────────────────────────────────────────────────

def list_folder_files(user: User, folder_id: str) -> FolderListResponse:
    """List all files directly inside a Drive folder (non-recursive)."""
    service = build_drive_client(user)
    query = f"'{folder_id}' in parents and trashed = false"
    fields = "files(id,name,mimeType,size,modifiedTime,webViewLink)"

    try:
        result = service.files().list(q=query, fields=fields, pageSize=200).execute()
    except HttpError as e:
        raise HTTPException(status_code=502, detail=f"Error al listar Drive: {e}")

    files = result.get("files", [])
    items = [
        DriveFileInfo(
            id=f["id"],
            name=f["name"],
            mime_type=f["mimeType"],
            size_bytes=int(f["size"]) if "size" in f else None,
            modified_at=datetime.fromisoformat(f["modifiedTime"].replace("Z", "+00:00"))
            if "modifiedTime" in f
            else None,
            web_view_link=f.get("webViewLink"),
        )
        for f in files
    ]
    return FolderListResponse(folder_id=folder_id, total=len(items), items=items)


# ── File download ─────────────────────────────────────────────────────────────

def _download_file(service, file_id: str, mime_type: str, dest: Path) -> None:
    """Download a Drive file to dest path, handling Google Docs export."""
    dest.parent.mkdir(parents=True, exist_ok=True)

    if mime_type in _GOOGLE_EXPORT_MIME:
        export_mime = _GOOGLE_EXPORT_MIME[mime_type]
        request = service.files().export_media(fileId=file_id, mimeType=export_mime)
    else:
        request = service.files().get_media(fileId=file_id)

    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    dest.write_bytes(buf.getvalue())


# ── Study sync ────────────────────────────────────────────────────────────────

async def sync_study(
    db: AsyncSession, user: User, study_id: UUID
) -> StudySyncResponse:
    """
    Download all corpus files for a study from its configured Drive folders.
    Creates/updates StudyCorpus records for each file found.
    """
    result = await db.execute(select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    if not study:
        raise HTTPException(status_code=404, detail="Estudio no encontrado")

    service = build_drive_client(user)
    base_storage = Path(settings.FILES_BASE_PATH) / str(study_id)

    fase_map: list[tuple[str, str | None]] = [
        ("FASE1", study.url_drive_fase1),
        ("FASE2", study.url_drive_fase2),
        ("FASE3", study.url_drive_fase3),
    ]

    sync_results: list[SyncResult] = []

    for fase, url in fase_map:
        if not url:
            continue

        folder_id = _extract_folder_id(url)
        if not folder_id:
            sync_results.append(SyncResult(
                study_id=study_id, fase=fase,
                files_found=0, files_downloaded=0, files_skipped=0,
                errors=[f"URL inválida de Drive para {fase}: {url}"],
            ))
            continue

        errors: list[str] = []
        downloaded = 0
        skipped = 0

        try:
            drive_files = _list_folder_recursive(service, folder_id)
        except HttpError as e:
            sync_results.append(SyncResult(
                study_id=study_id, fase=fase,
                files_found=0, files_downloaded=0, files_skipped=0,
                errors=[f"Error Drive API: {e}"],
            ))
            continue

        for df, rel_path in drive_files:
            mime = df.get("mimeType", "")
            tipo = _get_tipo(mime, df["name"])

            # Determinar nombre local con extensión correcta
            name = df["name"]
            if mime in _EXPORT_EXT and not name.endswith(_EXPORT_EXT[mime]):
                name += _EXPORT_EXT[mime]

            dest = base_storage / fase / rel_path / name if rel_path else base_storage / fase / name

            # Verificar si ya existe en corpus y está descargado
            existing_q = await db.execute(
                select(StudyCorpus).where(
                    StudyCorpus.study_id == study_id,
                    StudyCorpus.drive_file_id == df["id"],
                )
            )
            existing = existing_q.scalar_one_or_none()

            if existing and existing.estado == "descargado" and dest.exists():
                skipped += 1
                continue

            try:
                _download_file(service, df["id"], mime, dest)
            except Exception as e:
                errors.append(f"{name}: {e}")
                if existing:
                    existing.estado = "error"
                    existing.error_msg = str(e)
                continue

            size = int(df.get("size", 0)) if "size" in df else dest.stat().st_size

            if existing:
                existing.nombre_archivo = name
                existing.tipo_archivo = tipo
                existing.tamanio_bytes = size
                existing.ruta_local = str(dest)
                existing.estado = "descargado"
                existing.error_msg = None
                existing.sync_at = datetime.now(timezone.utc)
            else:
                corpus = StudyCorpus(
                    study_id=study_id,
                    fase=fase,
                    nombre_archivo=name,
                    drive_file_id=df["id"],
                    tipo_archivo=tipo,
                    tamanio_bytes=size,
                    ruta_local=str(dest),
                    estado="descargado",
                    sync_at=datetime.now(timezone.utc),
                )
                db.add(corpus)

            downloaded += 1

        await db.flush()

        sync_results.append(SyncResult(
            study_id=study_id,
            fase=fase,
            files_found=len(drive_files),
            files_downloaded=downloaded,
            files_skipped=skipped,
            errors=errors,
        ))


    # Actualizar drive_folder_id del estudio con el de FASE1 si no está seteado
    if not study.drive_folder_id:
        first_url = study.url_drive_fase1 or study.url_drive_fase2 or study.url_drive_fase3
        if first_url:
            study.drive_folder_id = _extract_folder_id(first_url)

    total_downloaded = sum(r.files_downloaded for r in sync_results)

    # Avanzar el estado: si se descargaron archivos y el estudio estaba en borrador → corpus_ok
    if total_downloaded > 0 and study.estado in ("borrador", "sincronizando"):
        study.estado = "corpus_ok"

    await db.flush()
    total_errors = sum(len(r.errors) for r in sync_results)

    return StudySyncResponse(
        study_id=study_id,
        fases=sync_results,
        total_downloaded=total_downloaded,
        total_errors=total_errors,
    )


# ── Listado y procesamiento unitario ─────────────────────────────────────────

def list_folder_by_url(user: User, url: str) -> FolderFilesResponse:
    """
    Lista todos los archivos de una carpeta Drive a partir de su URL.
    Recorre subcarpetas recursivamente. No descarga nada.
    """
    folder_id = _extract_folder_id(url)
    if not folder_id:
        raise HTTPException(
            status_code=400,
            detail="URL de carpeta Drive inválida. Debe tener el formato https://drive.google.com/drive/folders/…",
        )

    service = build_drive_client(user)

    try:
        raw = _list_folder_recursive(service, folder_id)
    except HttpError as e:
        raise HTTPException(status_code=502, detail=f"Error al acceder a Google Drive: {e}")

    items = [
        FolderFileItem(
            id=meta["id"],
            name=meta["name"],
            mime_type=meta["mimeType"],
            size_bytes=int(meta["size"]) if "size" in meta else None,
            subfolder=subfolder or None,
            tipo=_get_tipo(meta["mimeType"], meta["name"]),
            is_procesable=_get_tipo(meta["mimeType"], meta["name"]) in ("pdf", "docx"),
        )
        for meta, subfolder in raw
    ]
    return FolderFilesResponse(url=url, total=len(items), items=items)


_PROCESABLE_EXTS = {".pdf", ".docx", ".doc"}
_MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


async def process_single_file(
    db: AsyncSession,
    user: User,
    study_id: UUID,
    drive_file_id: str,
    file_name: str,
    mime_type: str,
    fase: str,
) -> dict:
    """
    Descarga UN archivo de Drive, extrae texto, genera resumen extractivo,
    guarda los resultados en BD y borra el archivo del disco inmediatamente.
    Nunca acumula archivos: el disco permanece casi vacío.
    """
    import tempfile
    from app.documents.extractor import process_document

    drive_svc = build_drive_client(user)

    # Ajustar nombre para documentos de Google exportados
    name = file_name
    if mime_type in _EXPORT_EXT and not name.endswith(_EXPORT_EXT[mime_type]):
        name += _EXPORT_EXT[mime_type]

    tipo = _get_tipo(mime_type, name)

    # Verificar si ya existe en el corpus
    existing_q = await db.execute(
        select(StudyCorpus).where(
            StudyCorpus.study_id == study_id,
            StudyCorpus.drive_file_id == drive_file_id,
        )
    )
    existing = existing_q.scalar_one_or_none()

    size = None
    resumen = None
    n_entidades = 0

    with tempfile.TemporaryDirectory() as tmpdir:
        dest = Path(tmpdir) / name

        # Descarga
        try:
            _download_file(drive_svc, drive_file_id, mime_type, dest)
            size = dest.stat().st_size
        except Exception as exc:
            # Registrar el error en el corpus y relanzar
            now_err = datetime.now(timezone.utc)
            if existing:
                existing.estado = "error"
                existing.error_msg = str(exc)[:300]
                existing.sync_at = now_err
            else:
                db.add(StudyCorpus(
                    study_id=study_id, fase=fase, nombre_archivo=name,
                    drive_file_id=drive_file_id, tipo_archivo=tipo,
                    estado="error", error_msg=str(exc)[:300], sync_at=now_err,
                ))
            await db.flush()
            raise HTTPException(status_code=502, detail=f"Error descargando '{name}': {exc}")

        # Extracción de texto (solo PDF/DOCX y < 50 MB)
        if dest.suffix.lower() in _PROCESABLE_EXTS and size < _MAX_SIZE_BYTES:
            try:
                doc_result = process_document(dest, source_name=name, model_name=settings.SPACY_MODEL)
                texto = (doc_result.get("texto") or "").strip()
                entidades = doc_result.get("entidades", [])

                if texto:
                    if len(texto) <= 500:
                        resumen = texto
                    else:
                        trunc = texto[:500]
                        cut = trunc.rfind(" ")
                        resumen = (trunc[:cut] if cut > 200 else trunc) + "…"

                now_ent = datetime.now(timezone.utc)
                for ent in entidades:
                    valor = (ent.get("valor") or "").strip()
                    if not valor or len(valor) < 2:
                        continue
                    db.add(CorpusExtraction(
                        study_id=study_id,
                        tipo_dato=ent.get("tipo_dato", "desconocido"),
                        valor=valor[:500],
                        fuente_archivo=name,
                        confianza=ent.get("confianza"),
                        extraido_en=now_ent,
                    ))
                n_entidades = len(entidades)
            except Exception as exc:
                resumen = f"[Extracción fallida: {str(exc)[:120]}]"
        # tmpdir sale del contexto → archivo borrado automáticamente

    # Guardar/actualizar registro en corpus
    now = datetime.now(timezone.utc)
    if existing:
        existing.nombre_archivo = name
        existing.tipo_archivo = tipo
        existing.tamanio_bytes = size
        existing.ruta_local = None
        existing.estado = "procesado"
        existing.error_msg = None
        existing.resumen = resumen
        existing.sync_at = now
        existing.procesado_en = now
    else:
        db.add(StudyCorpus(
            study_id=study_id, fase=fase, nombre_archivo=name,
            drive_file_id=drive_file_id, tipo_archivo=tipo,
            tamanio_bytes=size, ruta_local=None,
            estado="procesado", resumen=resumen,
            sync_at=now, procesado_en=now,
        ))

    await db.flush()

    # Avanzar estado del estudio si estaba en borrador
    study = await db.get(Study, study_id)
    if study and study.estado in ("borrador", "sincronizando"):
        study.estado = "corpus_ok"

    return {
        "drive_file_id": drive_file_id,
        "nombre_archivo": name,
        "tipo": tipo,
        "tamanio_bytes": size,
        "resumen": resumen,
        "n_entidades": n_entidades,
        "estado": "procesado",
    }


# ── Upload de informes a Drive ────────────────────────────────────────────────

def _find_or_create_subfolder(service, name: str, parent_id: str) -> str:
    """Busca una subcarpeta por nombre dentro de parent_id; la crea si no existe."""
    query = (
        f"name = '{name}' and '{parent_id}' in parents "
        f"and mimeType = '{_FOLDER_MIME}' and trashed = false"
    )
    result = service.files().list(q=query, fields="files(id)", pageSize=10).execute()
    files = result.get("files", [])
    if files:
        return files[0]["id"]
    folder = service.files().create(
        body={"name": name, "mimeType": _FOLDER_MIME, "parents": [parent_id]},
        fields="id",
    ).execute()
    return folder["id"]


def upload_report_to_drive(
    user: "User",
    fase3_url: str,
    pdf_bytes: bytes,
    filename: str,
) -> tuple[str, str]:
    """
    Sube el PDF del informe a FASE3/CONCEPTO/ en el Drive del estudio.

    Requiere que el usuario tenga un token de Drive con scope drive.file.
    Retorna (file_id, web_view_link).
    """
    service = build_drive_client(user)

    fase3_id = _extract_folder_id(fase3_url)
    if not fase3_id:
        raise ValueError(f"URL de FASE 3 inválida: {fase3_url}")

    concepto_id = _find_or_create_subfolder(service, "CONCEPTO", fase3_id)

    # Si ya existe un archivo con el mismo nombre, sobreescribirlo
    query = (
        f"name = '{filename}' and '{concepto_id}' in parents and trashed = false"
    )
    existing = service.files().list(q=query, fields="files(id)", pageSize=5).execute()
    existing_files = existing.get("files", [])

    media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype="application/pdf", resumable=False)

    if existing_files:
        file_id = existing_files[0]["id"]
        updated = service.files().update(
            fileId=file_id,
            media_body=media,
            fields="id,webViewLink",
        ).execute()
        return updated["id"], updated.get("webViewLink", "")
    else:
        created = service.files().create(
            body={"name": filename, "parents": [concepto_id], "mimeType": "application/pdf"},
            media_body=media,
            fields="id,webViewLink",
        ).execute()
        return created["id"], created.get("webViewLink", "")
