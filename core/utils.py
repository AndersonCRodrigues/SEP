from django.contrib.auth.models import Group
from .models import CustomUser
import secrets
import string
from django.core.mail import send_mail
from django.conf import settings



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
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def send_temporary_password_email(user,temporary_password):
    send_mail(
        subject="Seu acesso ao SEP",
        message=(
            f"Olá, {user.nome_completo}.\n\n"
            f"Sua conta foi criada no sistema SEP.\n"
            f"E-mail de acesso: {user.email}\n"
            f"Senha temporaria: {temporary_password} \n"
            f"Recomenta-se alterar sua senha nesse primeiro acesso"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False
    )