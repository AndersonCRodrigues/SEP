'''
Refs.:
https://docs.djangoproject.com/en/6.0/howto/custom-management-commands/
'''

import random
import os
from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from areas.models import AreaActing
from core.models import CustomUser
from core.utils import sincronizar_grupo
from patient.models import Patient
from students.models import Student
from teacher.models import Teacher

MODEL_BY_ROLE = {
    CustomUser.Role.PROFESSOR: Teacher,
    CustomUser.Role.ALUNO: Student,
    CustomUser.Role.PACIENTE: Patient,
}

DEFAULT_AREAS = [
    "Esquizoanálise",
    "TCC Adulto/Infantil",
    "Fenomenológico-Existencial",
    "Psicanálise",
]


def generate_valid_cpf():
    """Gera um CPF matematicamente válido para burlar a validação em ambiente de teste."""
    cpf = [random.randint(0, 9) for _ in range(9)]

    first_sum = sum(x * y for x, y in zip(cpf, range(10, 1, -1)))
    first_digit = 11 - (first_sum % 11)
    first_digit = 0 if first_digit >= 10 else first_digit
    cpf.append(first_digit)

    second_sum = sum(x * y for x, y in zip(cpf, range(11, 1, -1)))
    second_digit = 11 - (second_sum % 11)
    second_digit = 0 if second_digit >= 10 else second_digit
    cpf.append(second_digit)

    return f"{cpf[0]}{cpf[1]}{cpf[2]}.{cpf[3]}{cpf[4]}{cpf[5]}.{cpf[6]}{cpf[7]}{cpf[8]}-{cpf[9]}{cpf[10]}"


class Command(BaseCommand):
    help = 'Popula o banco de dados com áreas de atuação e usuários de teste.'

    def add_arguments(self, parser):
        # Permite passar roles separadas por espaço. ex.: --roles PR AL
        parser.add_argument(
            '--roles',
            nargs='+',
            type=str,
            choices=[role[0] for role in CustomUser.Role.choices],
            help='Especifica quais roles criar (SA SV PR AD AL PA). Se não for passado, cria uma de cada.'
        )

    def handle(self, *args, **options):
        if os.getenv("NODE_ENV") != "dev":
            self.stdout.write(self.style.WARNING(
                "popular_users só roda com NODE_ENV=dev. Nada foi criado."
            ))
            return

        areas = [AreaActing.objects.get_or_create(nome=name)[0] for name in DEFAULT_AREAS]
        self.stdout.write(self.style.SUCCESS("Áreas de Atuação verificadas/criadas com sucesso!"))

        selected_roles = options['roles'] or [role[0] for role in CustomUser.Role.choices]

        for role in selected_roles:
            prefix = role.lower()
            email = f"{prefix}@teste.com"
            counter = 1

            while CustomUser.objects.filter(email=email).exists():
                email = f"{prefix}{counter}@teste.com"
                counter += 1

            model = MODEL_BY_ROLE.get(role, CustomUser)
            extra_fields = {}
            if model is Teacher:
                extra_fields["acting_area"] = random.choice(areas)

            suffix = f" {counter}" if counter > 1 else ""
            user = model(
                email=email,
                nome_completo=f"Usuario Teste {role}{suffix}",
                cpf=generate_valid_cpf(),
                telefone="(99) 99999-9999",
                logradouro="Rua de Teste",
                numero="0",
                bairro="Centro",
                cidade="Maricá",
                estado="RJ",
                cep="24900-000",
                role=role,
                **extra_fields,
            )

            if role in (CustomUser.Role.ALUNO, CustomUser.Role.PROFESSOR, CustomUser.Role.ADMIN):
                user.matricula = f"2026{random.randint(1000, 9999)}"

            if role in (CustomUser.Role.PROFESSOR, CustomUser.Role.SUPERVISOR):
                user.crp = f"{random.randint(10000, 99999)}/RJ-{role}"

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
