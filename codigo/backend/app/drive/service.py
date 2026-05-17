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
from googleapiclient.http import MediaIoBaseDownload
from jose import jwt as jose_jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.config import get_settings
from app.drive.crypto import decrypt_token, encrypt_token
from app.drive.schemas import DriveFileInfo, FolderListResponse, SyncResult, StudySyncResponse
from app.studies.models import Study, StudyCorpus

settings = get_settings()

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

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
            tipo = _MIME_TO_TIPO.get(mime, "otro")

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
            await db.flush()

    total_downloaded = sum(r.files_downloaded for r in sync_results)
    total_errors = sum(len(r.errors) for r in sync_results)

    return StudySyncResponse(
        study_id=study_id,
        fases=sync_results,
        total_downloaded=total_downloaded,
        total_errors=total_errors,
    )
