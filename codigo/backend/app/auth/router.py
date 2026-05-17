from datetime import datetime, timezone
from jose import JWTError, jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database import get_db
from app.config import get_settings
from app.auth import schemas
from app.auth.service import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_user_by_id,
    hash_password,
    verify_password,
)
from app.auth.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


@router.post("/login", response_model=schemas.TokenResponse)
async def login(data: schemas.LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, data.email, data.password)

    # Actualizar ultimo_acceso
    user.ultimo_acceso = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)

    return schemas.TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=schemas.UserPublic.model_validate(user),
    )


@router.post("/refresh", response_model=schemas.TokenResponse)
async def refresh(data: schemas.RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(
            data.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload.get("type") != "refresh":
            raise ValueError
        user_id = UUID(payload["sub"])
    except (JWTError, ValueError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido")

    user = await get_user_by_id(db, user_id)
    if not user or user.estado != "activo":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")

    return schemas.TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=schemas.UserPublic.model_validate(user),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(_: User = Depends(get_current_user)):
    # Con JWT stateless el logout es responsabilidad del cliente (borra el token)
    # Para invalidación server-side se puede usar una blacklist en Redis
    return None


@router.get("/me", response_model=schemas.UserPublic)
async def me(current_user: User = Depends(get_current_user)):
    return schemas.UserPublic.model_validate(current_user)


@router.put("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    data: schemas.ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.password_nueva != data.password_nueva_confirmacion:
        raise HTTPException(status_code=400, detail="Las contraseñas nuevas no coinciden")
    if not verify_password(data.password_actual, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")

    current_user.password_hash = hash_password(data.password_nueva)
    await db.commit()
    return None
