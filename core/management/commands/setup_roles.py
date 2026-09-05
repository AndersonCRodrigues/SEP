from django.apps import apps
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from core.models import CustomUser
from core.permissions import BusinessRulesMixin
from core.user_management import MANAGEABLE_ROLES_BY
from core.utils import MAPA_GRUPOS

Role = CustomUser.Role

GERENCIAVEIS = {
    Role.PROFESSOR: "teacher.Teacher",
    Role.ALUNO: "students.Student",
    Role.PACIENTE: "patient.Patient",
}


def _rotulo(model, acao):
    return f"{model._meta.app_label}.{acao}_{model._meta.model_name}"


def _le(model, role):
    usuario = CustomUser(pk=0, role=role, is_superuser=role == Role.SUPERADMIN)
    return not model.objects.visible_to(usuario).query.is_empty()


def permissoes_por_role():
    """Projeta as regras declaradas nos models sobre o sistema de Permission."""
    por_role = {role: set() for role in MAPA_GRUPOS}

    for model in apps.get_models():
        if not issubclass(model, BusinessRulesMixin):
            continue
        for role in por_role:
            if model.creatable_by_role(role):
                por_role[role].add(_rotulo(model, "add"))
            if model.editable_fields_for_role(role):
                por_role[role].add(_rotulo(model, "change"))
            if model.deletable_by_role(role):
                por_role[role].add(_rotulo(model, "delete"))
            if _le(model, role):
                por_role[role].add(_rotulo(model, "view"))

    for ator, alvos in MANAGEABLE_ROLES_BY.items():
        for alvo in alvos:
            model = apps.get_model(GERENCIAVEIS.get(alvo, "core.CustomUser"))
            for acao in ("add", "change", "view"):
                por_role[ator].add(_rotulo(model, acao))

    return por_role


class Command(BaseCommand):
    help = (
        "Cria os Django Groups dos perfis e aplica as permissões declaradas nos models."
    )

    def handle(self, *args, **options):
        por_role = permissoes_por_role()

        for role, nome_grupo in MAPA_GRUPOS.items():
            grupo, criado = Group.objects.get_or_create(name=nome_grupo)
            status = "criado" if criado else "já existia"
            self.stdout.write(self.style.SUCCESS(f"Grupo '{nome_grupo}' {status}."))

            aplicadas = []
            for rotulo in sorted(por_role.get(role, ())):
                app_label, codename = rotulo.split(".")
                try:
                    aplicadas.append(
                        Permission.objects.get(
                            content_type__app_label=app_label, codename=codename
                        )
                    )
                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f"  '{rotulo}' não encontrada — pulando.")
                    )

            grupo.permissions.set(aplicadas)
            self.stdout.write(
                f"  {len(aplicadas)} permissões aplicadas em '{nome_grupo}'."
            )
