from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.auth.service import get_current_user, require_tecnico
from app.auth.models import User
from app.drive import service
from app.drive.schemas import (
    DriveAuthUrlResponse,
    DriveStatusResponse,
    FolderListResponse,
    StudySyncResponse,
)

router = APIRouter(prefix="/api/drive", tags=["drive"])
settings = get_settings()


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


@router.post("/sync/{study_id}", response_model=StudySyncResponse)
async def sync_study(
    study_id: UUID,
    current_user: User = Depends(require_tecnico),
    db: AsyncSession = Depends(get_db),
):
    """
    Descarga todos los archivos del corpus de un estudio desde Drive.
    Crea o actualiza los registros StudyCorpus correspondientes.
    """
    result = await service.sync_study(db, current_user, study_id)
    await db.commit()
    return result
