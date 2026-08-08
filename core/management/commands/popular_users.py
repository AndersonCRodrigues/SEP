'''
Refs.:
https://docs.djangoproject.com/en/6.0/howto/custom-management-commands/
'''


import random
import os
from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from core.models import CustomUser
from core.utils import sincronizar_grupo
from areas.models import AreaActing
from teacher.models import Professor
from students.models import Aluno


def gerar_cpf_valido():
    """Gera um CPF matematicamente válido para os testes."""
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
    help = 'Popula o banco de dados com áreas de atuação e usuários de teste.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--roles',
            nargs='+',
            type=str,
            choices=[role[0] for role in CustomUser.Role.choices],
            help='Especifica quais roles criar (SUPERADMIN, SUPERVISOR, PROFESSOR, ADMIN, ALUNO).'
        )

    def handle(self, *args, **options):
        areas_padrao = [
            "Esquizoanálise",
            "TCC Adulto/Infantil",
            "Fenomenológico-Existencial",
            "Psicanálise",
        ]
        objetos_area = []
        for nome_area in areas_padrao:
            area_obj, _ = AreaActing.objects.get_or_create(nome=nome_area)
            objetos_area.append(area_obj)

        self.stdout.write(self.style.SUCCESS("Áreas de Atuação verificadas/criadas com sucesso!"))

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

            cpf_dinamico = gerar_cpf_valido()
            matricula_gerada = f"2026{random.randint(1000, 9999)}"

            dados_base = dict(
                email=email,
                nome_completo=f"Usuario Teste {role} {contador if contador > 1 else ''}".strip(),
                cpf=cpf_dinamico,
                telefone="(99) 99999-9999",
                logradouro="Rua de Teste",
                numero="0",
                bairro="Centro",
                cidade="Maricá",
                estado="RJ",
                cep="24900-000",
                role=role,
                matricula=matricula_gerada if role != CustomUser.Role.SUPERADMIN else ""
            )

            # Escolhe a classe certa dependendo do role — Professor/Supervisor e Aluno
            # são subclasses de CustomUser (herança multi-tabela); os demais continuam CustomUser puro.
            if role in (CustomUser.Role.PROFESSOR, CustomUser.Role.SUPERVISOR):
                numero_crp = random.randint(10000, 99999)
                user = Professor(
                    **dados_base,
                    crp=f"{numero_crp}/RJ",
                    area_atuacao=random.choice(objetos_area),
                )
            elif role == CustomUser.Role.ALUNO:
                user = Aluno(**dados_base)
            else:
                user = CustomUser(**dados_base)
                if role == CustomUser.Role.SUPERADMIN:
                    user.is_staff = True
                    user.is_superuser = True

            user.set_password("SenhaForte123!")

            try:
                user.full_clean()
                user.save()
                sincronizar_grupo(user)
                self.stdout.write(self.style.SUCCESS(f"Usuário {role} ({email}) criado com sucesso!"))
            except ValidationError as e:
                self.stdout.write(self.style.ERROR(f"Erro de validação no usuário {role}: {e}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro inesperado no usuário {role}: {e}"))