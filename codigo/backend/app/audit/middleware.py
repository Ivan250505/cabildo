"""
Middleware de auditoría para FastAPI.
Registra automáticamente toda solicitud que modifica estado (POST/PUT/DELETE/PATCH).
Las lecturas (GET) no se auditan para evitar llenar el log.
"""
from __future__ import annotations

import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Registra en el log de la aplicación las solicitudes mutantes.
    El registro detallado en BD se hace a nivel de servicio para tener
    el contexto de usuario y estudio disponible.
    """

    SKIP_METHODS = {"GET", "HEAD", "OPTIONS"}
    SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next) -> Response:
        if (
            request.method in self.SKIP_METHODS
            or request.url.path in self.SKIP_PATHS
        ):
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 1)

        # Log estructurado a stdout — en producción un agente (Datadog, CloudWatch)
        # recoge estas líneas. No bloqueamos la respuesta escribiendo en BD aquí.
        import logging
        logger = logging.getLogger("etnosig.audit")
        logger.info(
            "%(method)s %(path)s %(status)s %(duration_ms)sms ip=%(ip)s",
            {
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "ip": request.client.host if request.client else "unknown",
            },
        )
        return response
