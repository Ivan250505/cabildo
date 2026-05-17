from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime
from typing import Literal


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserPublic"


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    password_actual: str
    password_nueva: str
    password_nueva_confirmacion: str


class UserPublic(BaseModel):
    id: UUID
    nombre_completo: str
    email: EmailStr
    rol: Literal["admin", "tecnico", "campo", "supervisor"]
    estado: Literal["activo", "suspendido"]
    ultimo_acceso: datetime | None = None

    model_config = {"from_attributes": True}
