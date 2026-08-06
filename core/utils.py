from django.contrib.auth.models import Group
from .models import CustomUser
import secrets
import string

MAPA_GRUPOS = {
    CustomUser.Role.SUPERADMIN: "Superadmin",
    CustomUser.Role.SUPERVISOR: "Supervisor",
    CustomUser.Role.ADMIN: "Administration",
    CustomUser.Role.PROFESSOR: "Professors",
    CustomUser.Role.ALUNO: "Students",
    CustomUser.Role.PACIENTE:"Patient",
}


def sincronizar_grupo(user):
    nome_grupo = MAPA_GRUPOS.get(user.role)
    if not nome_grupo:
        return
    grupo, _ = Group.objects.get_or_create(name=nome_grupo)
    user.groups.set([grupo])

def gerar_senha_temporaria(tamanho=8):
    caracteres = string.ascii_letters + string.digits
    senha_provisoria = ''.join(secrets.choice(caracteres) for _ in range(tamanho))
    return senha_provisoria