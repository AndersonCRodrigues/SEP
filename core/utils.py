import logging
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.mail import send_mail
from audit.models import SecurityLog
from .models import CustomUser

logger = logging.getLogger(__name__)

MAPA_GRUPOS = {
    CustomUser.Role.SUPERADMIN: "Superadmin",
    CustomUser.Role.SUPERVISOR: "Supervisor",
    CustomUser.Role.ADMINISTRATIVO: "Administration",
    CustomUser.Role.PROFESSOR: "Professors",
    CustomUser.Role.ALUNO: "Students",
    CustomUser.Role.PACIENTE: "Patient",
}


def sincronizar_grupo(user):
    nome_grupo = MAPA_GRUPOS.get(user.role)
    if not nome_grupo:
        return
    grupo, _ = Group.objects.get_or_create(name=nome_grupo)
    user.groups.set([grupo])


def generate_temporary_password(length=12):
    import secrets
    import string

    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def send_temporary_password_email(
    user, temporary_password, usuario_responsavel=None
):
    """Envia a senha temporária por e-mail e registra o log de auditoria (US-1.4)."""
    target_user = usuario_responsavel or user

    try:
        send_mail(
            subject="Seu acesso ao SEP",
            message=(
                f"Olá, {user.nome_completo}.\n\n"
                f"Sua conta foi criada no sistema SEP.\n"
                f"E-mail de acesso: {user.email}\n"
                f"Senha temporária: {temporary_password}\n\n"
                f"Recomenda-se alterar sua senha neste primeiro acesso."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        # Sucesso: usa Action.CREATE e o campo singular 'detail'
        SecurityLog.objects.create(
            user=target_user,
            user_identifier=getattr(target_user, "email", str(target_user)),
            action=SecurityLog.Action.CREATE,
            target_model=user.__class__.__name__,
            target_id=str(user.pk),
            detail=f"E-mail de boas-vindas com senha temporária enviado para {user.email}.",
        )

    except Exception as e:
        logger.error(
            f"Erro ao enviar e-mail de credenciais para {user.email}: {e}"
        )

        # Falha: usa o campo singular 'detail'
        SecurityLog.objects.create(
            user=target_user,
            user_identifier=getattr(target_user, "email", str(target_user)),
            action=SecurityLog.Action.CREATE,
            target_model=user.__class__.__name__,
            target_id=str(user.pk),
            detail=f"Falha SMTP ao enviar e-mail de credenciais para {user.email}: {str(e)}",
        )