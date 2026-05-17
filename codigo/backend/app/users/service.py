from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from fastapi import HTTPException, status

from app.auth.models import User
from app.auth.service import hash_password, get_user_by_email
from app.users.schemas import UserCreate, UserUpdate


async def list_users(
    db: AsyncSession,
    estado: str | None = None,
    rol: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[User], int]:
    query = select(User)
    if estado:
        query = query.where(User.estado == estado)
    if rol:
        query = query.where(User.rol == rol)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    query = query.offset((page - 1) * limit).limit(limit).order_by(User.nombre_completo)
    result = await db.execute(query)
    return result.scalars().all(), total


async def get_user_or_404(db: AsyncSession, user_id: UUID) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return user


async def create_user(db: AsyncSession, data: UserCreate) -> User:
    existing = await get_user_by_email(db, data.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email ya registrado")

    user = User(
        nombre_completo=data.nombre_completo,
        email=data.email.lower(),
        password_hash=hash_password(data.password),
        rol=data.rol,
        estado="activo",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def update_user(db: AsyncSession, user_id: UUID, data: UserUpdate) -> User:
    user = await get_user_or_404(db, user_id)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    await db.flush()
    await db.refresh(user)
    return user


async def delete_or_suspend_user(db: AsyncSession, user_id: UUID) -> None:
    user = await get_user_or_404(db, user_id)
    # Por seguridad solo suspendemos — eliminación física requiere confirmación adicional
    user.estado = "suspendido"
    await db.flush()


async def reset_password(db: AsyncSession, user_id: UUID, new_password: str) -> None:
    user = await get_user_or_404(db, user_id)
    user.password_hash = hash_password(new_password)
    await db.flush()
