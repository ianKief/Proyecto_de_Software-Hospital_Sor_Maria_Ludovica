import logging
from flask import current_app, render_template
from flask_mail import Mail, Message

logger = logging.getLogger(__name__)

mail = Mail()


def enviar_email(asunto, destinatarios, cuerpo_texto, cuerpo_html=None):
    """Envía un correo electrónico a través de Flask-Mail.
    
    Si el servidor SMTP no está disponible o falla, captura la excepción y 
    registra el contenido en los logs de la aplicación para permitir pruebas locales.
    """
    remitente = current_app.config.get("MAIL_DEFAULT_SENDER", "no-reply@hospital.com")
    mensaje = Message(
        subject=asunto,
        recipients=destinatarios if isinstance(destinatarios, list) else [destinatarios],
        body=cuerpo_texto,
        html=cuerpo_html,
        sender=remitente
    )

    try:
        # Solo intenta enviar si no estamos en testing y hay servidor configurado
        if not current_app.config.get("TESTING", False):
            mail.send(mensaje)
            logger.info("Correo enviado exitosamente a %s", destinatarios)
    except Exception as e:
        logger.warning("No se pudo enviar el correo mediante SMTP (%s). Mostrando contenido en log.", e)

    # Imprimir en consola para facilitar el desarrollo local sin necesidad de configurar SMTP
    print("\n" + "="*70)
    print(f"📧 [SIMULADOR DE EMAIL] Para: {destinatarios} | Asunto: {asunto}")
    print("-" * 70)
    print(cuerpo_texto.strip())
    print("="*70 + "\n")


def enviar_email_activacion(usuario, url_activacion):
    """Envía el email de bienvenida y activación para que el usuario configure su contraseña."""
    asunto = "Bienvenido/a al Sistema de Gestión del Hospital - Activá tu cuenta"
    cuerpo_texto = f"""
Hola {usuario.nombre} {usuario.apellido}:

Fuiste dado/a de alta en el Sistema de Gestión del Hospital Sor María Ludovica.

Para activar tu cuenta y configurar tu contraseña de acceso, por favor ingresá al siguiente enlace:
{url_activacion}

Este enlace es válido durante 24 horas.

Saludos cordiales,
Equipo de Administración
Hospital Sor María Ludovica
"""
    cuerpo_html = render_template(
        "emails/activacion.html",
        usuario=usuario,
        url_activacion=url_activacion
    )
    enviar_email(asunto, usuario.email, cuerpo_texto, cuerpo_html)


def enviar_email_magic_login(usuario, url_login):
    """Envía el email de inicio de sesión sin contraseña (Magic Link)."""
    asunto = "Tu enlace de acceso al Sistema de Gestión del Hospital"
    cuerpo_texto = f"""
Hola {usuario.nombre}:

Recibimos una solicitud para iniciar sesión en tu cuenta sin contraseña.

Hacé clic en el siguiente enlace para ingresar directamente:
{url_login}

Este enlace es de un solo uso y vencerá en 15 minutos.
Si vos no solicitaste este acceso, podés ignorar este correo de forma segura.

Saludos,
Hospital Sor María Ludovica
"""
    cuerpo_html = render_template(
        "emails/magic_login.html",
        usuario=usuario,
        url_login=url_login
    )
    enviar_email(asunto, usuario.email, cuerpo_texto, cuerpo_html)
