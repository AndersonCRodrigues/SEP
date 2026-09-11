import os
import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand

from areas.models import AreaActing
from core.models import CustomUser
from patient.models import Patient
from students.models import Advising, Student, StudentActivity
from teacher.models import Teacher


class Command(BaseCommand):
    help = (
        "Conecta os usuarios criados pelo populate_users entre si "
        "(vincula aluno a professor, atividades de exemplo), para "
        "testar telas com dado real, nao so vazio."
    )

    def handle(self, *args, **options):
        if os.getenv("NODE_ENV") != "dev":
            self.stdout.write(
                self.style.WARNING(
                    "Ignorado: populate_demo_relations só roda com NODE_ENV=dev."
                )
            )
            return

        professores = list(Teacher.objects.filter(role=CustomUser.Role.PROFESSOR))
        alunos = list(Student.objects.filter(current_advisor__isnull=True))

        if not professores or not alunos:
            self.stdout.write(
                self.style.WARNING(
                    "Nao ha professores ou alunos suficientes. "
                    "Rode 'populate_users --qtd 3' antes."
                )
            )
            return

        vinculados = 0
        for aluno in alunos:
            professor = random.choice(professores)  # nosec B311
            Advising.objects.change_advisor(aluno, professor, term="2026.1")
            vinculados += 1

        self.stdout.write(
            self.style.SUCCESS(f"{vinculados} aluno(s) vinculado(s) a um professor.")
        )

        area = AreaActing.objects.first()
        atividades_criadas = 0
        for aluno in Student.objects.filter(current_advisor__isnull=False):
            professor = aluno.current_advisor
            StudentActivity.objects.create(
                student=aluno,
                date=date.today() - timedelta(days=random.randint(1, 10)),  # nosec B311
                activity_type=StudentActivity.ActivityType.SESSION,
                hours_worked=random.choice(["1.00", "1.50", "2.00"]),  # nosec B311
                notes="Atividade de demonstracao criada por populate_demo_relations.",
                responsible_supervisor=professor,
            )
            atividades_criadas += 1

        self.stdout.write(
            self.style.SUCCESS(f"{atividades_criadas} atividade(s) de exemplo criada(s).")
        )