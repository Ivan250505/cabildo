"""
Servicio de notificaciones por email.
Usa aiosmtplib para envío asíncrono sin bloquear el event loop.
"""
from __future__ import annotations

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.config import get_settings

logger = logging.getLogger("etnosig.notifications")
settings = get_settings()


# ── Envío base ────────────────────────────────────────────────────────────────

async def send_email(
    to: str | list[str],
    subject: str,
    html_body: str,
    text_body: str | None = None,
) -> bool:
    """
    Envía un email HTML con fallback a texto plano.
    Retorna True si el envío fue exitoso, False si no está configurado o falla.
    """
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("SMTP no configurado — email no enviado: %s", subject)
        return False

    recipients = [to] if isinstance(to, str) else to

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.FROM_EMAIL
    msg["To"] = ", ".join(recipients)

    if text_body:
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            start_tls=True,
        )
        logger.info("Email enviado a %s: %s", recipients, subject)
        return True
    except Exception as e:
        logger.error("Error enviando email a %s: %s", recipients, e)
        return False


# ── Plantillas de notificación ────────────────────────────────────────────────

def _base_html(titulo: str, cuerpo: str) -> str:
    return f"""
    <html><body style="font-family:Calibri,sans-serif;color:#1A1A1A;max-width:600px;margin:auto">
      <div style="background:#1A3A5C;padding:20px;text-align:center">
        <h1 style="color:#fff;margin:0;font-size:22px">EtnoSIG</h1>
        <p style="color:#C8922A;margin:4px 0 0">Simonky S.A.S.</p>
      </div>
      <div style="padding:24px 20px">
        <h2 style="color:#B22222">{titulo}</h2>
        {cuerpo}
      </div>
      <div style="background:#f5f5f5;padding:12px;text-align:center;font-size:11px;color:#666">
        Este es un mensaje automático del sistema EtnoSIG. No responda este correo.
      </div>
    </body></html>
    """


async def notify_listo_revision(
    to: str,
    nombre_comunidad: str,
    study_id: str,
) -> None:
    """Notifica al supervisor que un estudio está listo para revisión."""
    html = _base_html(
        "Estudio listo para revisión",
        f"""
        <p>El estudio de la comunidad <strong>{nombre_comunidad}</strong>
        ha completado el procesamiento y está listo para revisión.</p>
        <p><strong>ID del estudio:</strong> {study_id}</p>
        <p>Ingrese al sistema EtnoSIG para revisar y aprobar el informe generado.</p>
        <a href="#" style="background:#B22222;color:#fff;padding:10px 20px;
           text-decoration:none;border-radius:4px;display:inline-block;margin-top:12px">
          Ver estudio
        </a>
        """,
    )
    await send_email(
        to=to,
        subject=f"[EtnoSIG] Estudio listo para revisión: {nombre_comunidad}",
        html_body=html,
        text_body=f"El estudio {nombre_comunidad} (ID: {study_id}) está listo para revisión.",
    )


async def notify_aprobado(
    to: str,
    nombre_comunidad: str,
    study_id: str,
) -> None:
    """Notifica al técnico que su informe fue aprobado."""
    html = _base_html(
        "Informe aprobado",
        f"""
        <p>El informe del estudio <strong>{nombre_comunidad}</strong>
        ha sido <strong style="color:#2E7D32">aprobado</strong> por el supervisor.</p>
        <p><strong>ID del estudio:</strong> {study_id}</p>
        <p>El documento puede ser descargado y enviado al Ministerio del Interior.</p>
        """,
    )
    await send_email(
        to=to,
        subject=f"[EtnoSIG] Informe aprobado: {nombre_comunidad}",
        html_body=html,
        text_body=f"El informe de {nombre_comunidad} (ID: {study_id}) fue aprobado.",
    )


async def notify_error(
    to: str,
    nombre_comunidad: str,
    study_id: str,
    error_msg: str,
) -> None:
    """Notifica a técnico y admin que ocurrió un error en el procesamiento."""
    html = _base_html(
        "Error en procesamiento",
        f"""
        <p>Ocurrió un error al procesar el estudio
        <strong>{nombre_comunidad}</strong>.</p>
        <p><strong>ID del estudio:</strong> {study_id}</p>
        <p><strong>Error:</strong></p>
        <pre style="background:#f5f5f5;padding:12px;border-radius:4px;
             font-size:12px;color:#B22222">{error_msg[:500]}</pre>
        <p>Ingrese al sistema para revisar y corregir el problema.</p>
        """,
    )
    await send_email(
        to=to,
        subject=f"[EtnoSIG] Error en procesamiento: {nombre_comunidad}",
        html_body=html,
        text_body=f"Error en estudio {nombre_comunidad} (ID: {study_id}): {error_msg[:200]}",
    )


async def notify_password_reset(to: str, nombre: str, temp_password: str) -> None:
    """Envía la contraseña temporal al usuario."""
    html = _base_html(
        "Contraseña temporal",
        f"""
        <p>Hola <strong>{nombre}</strong>,</p>
        <p>Se ha generado una contraseña temporal para su cuenta en EtnoSIG:</p>
        <p style="font-size:24px;font-weight:bold;letter-spacing:4px;
           color:#1A3A5C;text-align:center;padding:16px;background:#f5f5f5;
           border-radius:4px">{temp_password}</p>
        <p>Por seguridad, cambie esta contraseña inmediatamente después de iniciar sesión
        en <em>Perfil → Cambiar contraseña</em>.</p>
        """,
    )
    await send_email(
        to=to,
        subject="[EtnoSIG] Contraseña temporal de acceso",
        html_body=html,
        text_body=f"Hola {nombre}, su contraseña temporal es: {temp_password}",
    )
