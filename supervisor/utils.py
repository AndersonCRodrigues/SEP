import os
import string
import secrets
import logging
from django.core.mail import send_mail
from django.conf import settings
from audit.models import SecurityLog

logger = logging.getLogger(__name__)


def gerar_senha_temporaria(tamanho=8):
    caracteres = string.ascii_letters + string.digits
    senha_provisoria = "".join(secrets.choice(caracteres) for _ in range(tamanho))
    return senha_provisoria


def enviar_email_credenciais(user, senha_temporaria, usuario_responsavel=None):
    """
    Envia o e-mail de boas-vindas com a senha temporária,
    garantindo resiliência (try/except) e registro de auditoria (US-1.4).
    """
    link_portal = os.getenv("PORTAL_PACIENTE_URL", "URL_NAO_CONFIGURADA")

    mensagem = f"Olá {user.nome_completo}, seu cadastro foi realizado. Sua senha temporária é: {senha_temporaria}. Acesse o portal do paciente em {link_portal}."

    try:
        send_mail(
            subject="Bem-vindo ao Portal do Paciente",
            message=mensagem,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        SecurityLog.objects.create(
            user=usuario_responsavel or user,
            action="EMAIL_BOAS_VINDAS_ENVIADO",
            target_model="Patient",
            target_id=user.pk,
        )

    except Exception as e:
        logger.error(f"Erro ao enviar e-mail de credenciais para {user.email}: {e}")

        SecurityLog.objects.create(
            user=usuario_responsavel or user,
            action="FALHA_ENVIO_EMAIL",
            details=f"Erro SMTP ao tentar notificar {user.email}: {str(e)}",
            target_model="Patient",
            target_id=user.pk,
        )
