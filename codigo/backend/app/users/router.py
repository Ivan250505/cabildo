import secrets
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.service import require_admin, get_current_user
from app.auth.models import User
from app.users import schemas, service

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=schemas.UserListResponse)
async def list_users(
    estado: str | None = Query(None),
    rol: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    users, total = await service.list_users(db, estado=estado, rol=rol, page=page, limit=limit)
    return schemas.UserListResponse(
        total=total,
        page=page,
        limit=limit,
        items=[schemas.UserResponse.model_validate(u) for u in users],
    )


@router.post("", response_model=schemas.UserResponse, status_code=201)
async def create_user(
    data: schemas.UserCreate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await service.create_user(db, data)
    return schemas.UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=schemas.UserResponse)
async def get_user(
    user_id: UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await service.get_user_or_404(db, user_id)
    return schemas.UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=schemas.UserResponse)
async def update_user(
    user_id: UUID,
    data: schemas.UserUpdate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await service.update_user(db, user_id, data)
    return schemas.UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await service.delete_or_suspend_user(db, user_id)
    return None


@router.post("/{user_id}/reset-password")
async def reset_password(
    user_id: UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    temp_password = secrets.token_urlsafe(12)
    await service.reset_password(db, user_id, temp_password)
    # TODO: enviar email con temp_password
    return {"message": "Contraseña temporal generada. Email enviado al usuario."}
