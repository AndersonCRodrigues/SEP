import os
import random

from django.core.management.base import BaseCommand
from django.db import transaction

from areas.models import AreaActing
from core.models import CustomUser
from core.utils import sincronizar_grupo
from teacher.models import Teacher

INITIAL_PASSWORD = "PrimeiroAcesso@123"  # nosec B105

ADDRESS = dict(
    telefone="21999990000",
    logradouro="Rua da Demonstração",
    numero="10",
    bairro="Centro",
    cidade="Maricá",
    estado="RJ",
    cep="24900-000",
)

ACCOUNTS = (
    {
        "model": Teacher,
        "email": "professor.primeiro@teste.com",
        "first_name": "Helena",
        "last_name": "Prado",
        "role": CustomUser.Role.PROFESSOR,
        "extra": {"crp": "05/20001", "matricula": "PA20260001"},
    },
    {
        "model": CustomUser,
        "email": "administrativo.primeiro@teste.com",
        "first_name": "Carla",
        "last_name": "Nogueira",
        "role": CustomUser.Role.ADMINISTRATIVO,
        "extra": {"matricula": "PA20260002"},
    },
)


def valid_cpf():
    digits = [random.randint(0, 9) for _ in range(9)]  # nosec B311
    for size in (10, 11):
        remainder = 11 - sum(d * w for d, w in zip(digits, range(size, 1, -1))) % 11
        digits.append(0 if remainder >= 10 else remainder)
    return "".join(map(str, digits))


class Command(BaseCommand):
    help = (
        "Cria um Professor e um Administrativo em situação de primeiro acesso, "
        "que são levados à troca de senha obrigatória ao entrar."
    )

    def handle(self, *args, **options):
        if os.getenv("NODE_ENV") != "dev":
            self.stdout.write(
                self.style.WARNING(
                    "Ignorado: populate_first_access só roda com NODE_ENV=dev."
                )
            )
            return

        area = AreaActing.objects.first()
        if area is None:
            self.stdout.write(
                self.style.ERROR(
                    "Faltam áreas de atuação. Rode antes: manage.py populate_users"
                )
            )
            return

        with transaction.atomic():
            users = [self.first_access_user(account) for account in ACCOUNTS]
            for user in users:
                if isinstance(user, Teacher):
                    user.acting_areas.set([area])

        self.summarize(users)

    @staticmethod
    def first_access_user(account):
        model = account["model"]
        user = model.objects.filter(email=account["email"]).first()
        if user is None:
            user = model(
                email=account["email"],
                first_name=account["first_name"],
                last_name=account["last_name"],
                cpf=valid_cpf(),
                **account["extra"],
                **ADDRESS,
            )

        user.role = account["role"]
        user.is_active = True
        user.must_change_password = True
        user.set_password(INITIAL_PASSWORD)
        user.save()
        sincronizar_grupo(user)
        return user

    def summarize(self, users):
        self.stdout.write(self.style.SUCCESS("Usuários de primeiro acesso prontos."))
        self.stdout.write("")
        self.stdout.write("Entre com uma destas contas para ver a troca de senha:")
        for user in users:
            self.stdout.write(f"  {user.get_role_display():<15}: {user.email}")
        self.stdout.write(f"  Senha inicial  : {INITIAL_PASSWORD}")
        self.stdout.write("")
        self.stdout.write(
            "Depois de trocar a senha a conta sai do primeiro acesso. Rode este "
            "comando de novo para voltar ao primeiro acesso com a senha inicial."
        )
