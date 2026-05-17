"""
Servicio de auditoría.
Registra acciones críticas en AuditLog de forma inmutable.
"""
from __future__ import annotations

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.studies.models import AuditLog


async def log_action(
    db: AsyncSession,
    accion: str,
    user_id: UUID | None = None,
    study_id: UUID | None = None,
    detalle: dict | None = None,
    ip_address: str | None = None,
) -> None:
    """
    Inserta un registro de auditoría. No hace flush ni commit —
    se espera que el llamador lo haga junto con la transacción principal.
    """
    entry = AuditLog(
        user_id=user_id,
        study_id=study_id,
        accion=accion,
        detalle=detalle or {},
        ip_address=ip_address,
    )
    db.add(entry)
