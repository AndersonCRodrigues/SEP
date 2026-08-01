from django.contrib.auth.models import Group
from .models import CustomUser


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