from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, Query, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db, AsyncSessionLocal
from app.auth.service import get_current_user, require_tecnico
from app.auth.models import User
from app.studies.models import Study
from app.drive import service
from app.drive.schemas import (
    DriveAuthUrlResponse,
    DriveStatusResponse,
    FolderListResponse,
    FolderFilesResponse,
    ProcessFileRequest,
    ProcessFileResponse,
)

router = APIRouter(prefix="/api/drive", tags=["drive"])
settings = get_settings()


async def _bg_sync(study_id: UUID, user_id: UUID) -> None:
    async with AsyncSessionLocal() as db:
        try:
            user = await db.get(User, user_id)
            if not user:
                return
            await service.sync_study(db, user, study_id)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            async with AsyncSessionLocal() as db2:
                study = await db2.get(Study, study_id)
                if study and study.estado == "sincronizando":
                    study.estado = "borrador"
                    study.error_msg = f"Sync fallido: {str(exc)[:300]}"
                    await db2.commit()


@router.get("/auth-url", response_model=DriveAuthUrlResponse)
async def get_auth_url(current_user: User = Depends(get_current_user)):
    """Genera la URL de autorización de Google OAuth2. Codifica user_id en el state."""
    url, state = service.generate_auth_url(str(current_user.id))
    return DriveAuthUrlResponse(url=url, state=state)


@router.get("/callback")
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Callback OAuth2 de Google. No requiere JWT: el user_id viene firmado en el state.
    Intercambia el código por tokens, los guarda cifrados y redirige al frontend.
    """
    # Identificar al usuario desde el state firmado
    user_id = service.decode_oauth_state(state)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    await service.exchange_code(db, user, code)
    await db.commit()

    return RedirectResponse(url=f"{settings.FRONTEND_URL}?drive_connected=true")


@router.get("/status", response_model=DriveStatusResponse)
async def drive_status(current_user: User = Depends(get_current_user)):
    """Indica si el usuario tiene una cuenta de Google conectada."""
    if not current_user.google_token:
        return DriveStatusResponse(connected=False)
    info = service.get_drive_user_info(current_user)
    return DriveStatusResponse(
        connected=True,
        google_email=info.get("emailAddress") if info else None,
    )


@router.delete("/revoke", status_code=204)
async def revoke_drive(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Desconecta la cuenta de Google eliminando el token almacenado."""
    await service.revoke_token(db, current_user)
    await db.commit()
    return None


@router.get("/folders/{folder_id}", response_model=FolderListResponse)
async def list_folder(
    folder_id: str,
    current_user: User = Depends(get_current_user),
):
    """Lista los archivos dentro de una carpeta de Google Drive."""
    return service.list_folder_files(current_user, folder_id)


@router.get("/folder-files", response_model=FolderFilesResponse)
async def list_drive_folder(
    url: str = Query(..., description="URL completa de la carpeta de Google Drive"),
    current_user: User = Depends(get_current_user),
):
    """
    Lista todos los archivos de una carpeta Drive (recursivo, sin descargar nada).
    Devuelve metadatos: id, nombre, tipo, tamaño, subcarpeta.
    """
    return service.list_folder_by_url(current_user, url)


@router.post("/process-file/{study_id}", response_model=ProcessFileResponse)
async def process_drive_file(
    study_id: UUID,
    body: ProcessFileRequest,
    current_user: User = Depends(require_tecnico),
    db: AsyncSession = Depends(get_db),
):
    """
    Descarga UN archivo de Drive, extrae texto, genera resumen, guarda en BD y borra el archivo.
    Llamar de uno en uno desde el frontend para control de progreso sin timeout.
    """
    result = await service.process_single_file(
        db, current_user, study_id,
        body.drive_file_id, body.file_name, body.mime_type, body.fase,
    )
    await db.commit()
    return result


@router.post("/sync/{study_id}", status_code=202)
async def sync_study(
    study_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_tecnico),
    db: AsyncSession = Depends(get_db),
):
    """
    Inicia la sincronización del corpus desde Google Drive en segundo plano.
    Devuelve 202 inmediatamente; sondea GET /api/studies/{id} para ver el estado.
    """
    r = await db.execute(select(Study).where(Study.id == study_id))
    study = r.scalar_one_or_none()
    if not study:
        raise HTTPException(status_code=404, detail="Estudio no encontrado")
    study.estado = "sincronizando"
    await db.commit()
    background_tasks.add_task(_bg_sync, study_id, current_user.id)
    return {"status": "sincronizando", "study_id": str(study_id)}
