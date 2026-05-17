from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime
from typing import Literal


class UserCreate(BaseModel):
    nombre_completo: str
    email: EmailStr
    password: str
    rol: Literal["admin", "tecnico", "campo", "supervisor"]


class UserUpdate(BaseModel):
    nombre_completo: str | None = None
    rol: Literal["admin", "tecnico", "campo", "supervisor"] | None = None
    estado: Literal["activo", "suspendido"] | None = None


class UserResponse(BaseModel):
    id: UUID
    nombre_completo: str
    email: EmailStr
    rol: str
    estado: str
    estudios_asignados: int = 0
    ultimo_acceso: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    total: int
    page: int
    limit: int
    items: list[UserResponse]
