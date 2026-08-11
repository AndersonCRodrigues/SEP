'''
Refs.:
https://docs.djangoproject.com/en/6.0/howto/custom-management-commands/
'''
import random
import os
from datetime import date
from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from core.models import CustomUser
from core.utils import sincronizar_grupo
from areas.models import AreaActing
from teacher.models import Professor
from students.models import Aluno


def gerar_cpf_valido():
    """Gera um CPF matematicamente válido para burlar a validação em ambiente de teste."""
    cpf = [random.randint(0, 9) for _ in range(9)]

    soma1 = sum(x * y for x, y in zip(cpf, range(10, 1, -1)))
    d1 = 11 - (soma1 % 11)
    d1 = 0 if d1 >= 10 else d1
    cpf.append(d1)

    soma2 = sum(x * y for x, y in zip(cpf, range(11, 1, -1)))
    d2 = 11 - (soma2 % 11)
    d2 = 0 if d2 >= 10 else d2
    cpf.append(d2)

    return f"{cpf[0]}{cpf[1]}{cpf[2]}.{cpf[3]}{cpf[4]}{cpf[5]}.{cpf[6]}{cpf[7]}{cpf[8]}-{cpf[9]}{cpf[10]}"


class Command(BaseCommand):
    help = 'Popula o banco de dados com usuários de teste para as Roles selecionadas. Só roda se NODE_ENV=dev.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--roles',
            nargs='+',
            type=str,
            choices=[role[0] for role in CustomUser.Role.choices],
            help='Especifica quais roles criar. Valores aceitos: SUPERADMIN, SUPERVISOR, PROFESSOR, ADMIN, ALUNO.'
        )

    def handle(self, *args, **options):
        if os.getenv("NODE_ENV") != "dev":
            self.stdout.write(self.style.WARNING(
                "NODE_ENV != 'dev' — comando ignorado (evita popular dados de teste em produção)."
            ))
            return

        area_padrao, _ = AreaActing.objects.get_or_create(nome="Psicanálise")

        roles_selecionadas = options['roles']
        if not roles_selecionadas:
            roles_selecionadas = [role[0] for role in CustomUser.Role.choices]

        for role in roles_selecionadas:
            prefixo = role.lower()
            email = f"{prefixo}@teste.com"
            contador = 1

            while CustomUser.objects.filter(email=email).exists():
                email = f"{prefixo}{contador}@teste.com"
                contador += 1

            campos_base = dict(
                email=email,
                nome_completo=f"Usuario Teste {role} {contador if contador > 1 else ''}".strip(),
                cpf=gerar_cpf_valido(),
                telefone="(99) 99999-9999",
                data_nascimento=date(1995, 1, 1),
                logradouro="Rua de Teste",
                numero="0",
                bairro="Centro",
                cidade="Maricá",
                estado="RJ",
                cep="24900-000",
                role=role,
            )

            if role in (CustomUser.Role.PROFESSOR, CustomUser.Role.SUPERVISOR):
                numero_crp = random.randint(10000, 99999)
                user = Professor(
                    **campos_base,
                    crp=f"{numero_crp}/RJ-{role}",
                    area_atuacao=area_padrao,
                )
            elif role == CustomUser.Role.ALUNO:
                numero_aleatorio = random.randint(1000, 9999)
                user = Aluno(**campos_base, matricula=f"2026{numero_aleatorio}")
            elif role == CustomUser.Role.ADMINISTRATIVO:
                numero_aleatorio = random.randint(1000, 9999)
                user = CustomUser(**campos_base, matricula=f"2026{numero_aleatorio}")
            else:
                user = CustomUser(**campos_base)
                if role == CustomUser.Role.SUPERADMIN:
                    user.is_staff = True
                    user.is_superuser = True

            user.set_password("Senha123!")

            try:
                user.full_clean()
                user.save()
                sincronizar_grupo(user)
                self.stdout.write(self.style.SUCCESS(f"Usuário {role} ({email}) criado com sucesso!"))
            except ValidationError as e:
                self.stdout.write(self.style.ERROR(f"Erro de validação no usuário {role}: {e}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro inesperado no usuário {role}: {e}"))