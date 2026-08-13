from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from core.models import CustomUser


MAPA_GRUPOS = {
    CustomUser.Role.SUPERADMIN: "Superadmin",
    CustomUser.Role.SUPERVISOR: "Supervisor",
    CustomUser.Role.ADMINISTRATIVO: "Administration",
    CustomUser.Role.PROFESSOR: "Professors",
    CustomUser.Role.ALUNO: "Students",
}

PERMISSOES_BASE = {
    "Superadmin": [],
    "Administration": [
        "core.add_customuser",
        "core.change_customuser",
        "core.view_customuser",
    ],
    "Professors": [
        "students.view_aluno",
        "students.add_orientacao",
        "students.view_orientacao",
        "students.change_orientacao",
        "teacher.change_professor",
        "areas.view_areaacting",
    ],
    "Students": [
        "students.view_orientacao",
    ],
    "Supervisor": [
        "teacher.add_professor",
        "teacher.view_professor",
        "teacher.change_professor",
        "students.add_aluno",
        "students.view_aluno",
        "students.change_aluno",
        "students.add_orientacao",
        "students.view_orientacao",
        "students.change_orientacao",
        "areas.add_areaacting",
        "areas.change_areaacting",
        "areas.view_areaacting",
    ],
}


class Command(BaseCommand):
    help = "Cria os Django Groups mapeados pros perfis (exceto Paciente) com permissões base."

    def handle(self, *args, **options):
        for role, nome_grupo in MAPA_GRUPOS.items():
            grupo, criado = Group.objects.get_or_create(name=nome_grupo)
            status = "criado" if criado else "já existia"
            self.stdout.write(self.style.SUCCESS(f"Grupo '{nome_grupo}' {status}."))

            permissoes_aplicadas = []
            for codename_completo in PERMISSOES_BASE.get(nome_grupo, []):
                app_label, codename = codename_completo.split(".")
                try:
                    permissao = Permission.objects.get(
                        content_type__app_label=app_label, codename=codename
                    )
                    permissoes_aplicadas.append(permissao)
                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  Permissão '{codename_completo}' não encontrada — pulando."
                        )
                    )

            grupo.permissions.set(permissoes_aplicadas)
            self.stdout.write(
                f"  {len(permissoes_aplicadas)} permissões aplicadas em '{nome_grupo}'."
            )
