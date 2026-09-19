import os
import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand

from areas.models import AreaActing
from core.management.commands.populate_users import generate_valid_cpf
from core.models import CustomUser
from patient.models import Patient, ProgressNote
from students.models import (
    Advising,
    CaseAssignment,
    PerformanceReview,
    Student,
    StudentActivity,
)
from teacher.models import Teacher

ENDERECO_PADRAO = dict(
    telefone="(99) 99999-9999",
    logradouro="Rua de Teste",
    numero="0",
    bairro="Centro",
    cidade="Maricá",
    estado="RJ",
    cep="24900-000",
)


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

        self._criar_pacientes_mock(area, professores)

    def _criar_pacientes_mock(self, area, professores):
        """MOCK temporário: cria pacientes em triagem (REFERRED) e em
        atendimento (IN_TREATMENT, com CaseAssignment + ProgressNote +
        PerformanceReview) só para dar conteúdo às telas de Prontuários,
        Avaliações/Triagem e Presença/Feedback enquanto as integrações
        reais (fluxo de encaminhamento, regra de vagas por paciente) não
        viram task. Substituir/remover quando essas telas tiverem dado
        de verdade vindo do fluxo do paciente/aluno.
        """
        alunos = list(Student.objects.filter(current_advisor__isnull=False))
        if not alunos or area is None or not professores:
            self.stdout.write(
                self.style.WARNING(
                    "Sem alunos vinculados, área de atuação ou professor "
                    "cadastrado — rode populate_users antes de "
                    "populate_demo_relations."
                )
            )
            return

        # --- Pacientes aguardando triagem (aparecem em "Definição de triagem") ---
        criados_triagem = 0
        for i in range(3):
            email = f"paciente.triagem{i}@teste.com"
            if Patient.objects.filter(email=email).exists():
                continue

            paciente = Patient(
                email=email,
                nome_completo=f"Paciente Triagem {i + 1}",
                cpf=generate_valid_cpf(),
                data_nascimento=date(1995, 1, 1) - timedelta(days=i * 365),
                role=CustomUser.Role.PACIENTE,
                flow_status=Patient.FlowStatus.REFERRED,
                **ENDERECO_PADRAO,
            )
            paciente.set_password("SenhaForte123!")
            paciente.save()

            # Sem isso o professor nunca enxerga o paciente em "Avaliações":
            # visible_to() só libera REFERRED se o professor estiver em
            # responsible_teachers (ainda não há caso/CaseAssignment aqui).
            professor_designado = professores[i % len(professores)]
            paciente.responsible_teachers.set([professor_designado])

            criados_triagem += 1

        # --- Pacientes em atendimento (Prontuários + Presença/Feedback) ---
        criados_atendimento = 0
        for i, aluno in enumerate(alunos):
            email = f"paciente.atendimento{i}@teste.com"
            if Patient.objects.filter(email=email).exists():
                continue

            paciente = Patient(
                email=email,
                nome_completo=f"Paciente Atendimento {i + 1}",
                cpf=generate_valid_cpf(),
                data_nascimento=date(1990, 6, 15),
                role=CustomUser.Role.PACIENTE,
                **ENDERECO_PADRAO,
            )
            paciente.set_password("SenhaForte123!")
            paciente.save()

            CaseAssignment.objects.assign(
                student=aluno, patient=paciente, acting_area=area
            )

            ProgressNote.objects.create(
                patient=paciente,
                student=aluno,
                acting_area=area,
                content=(
                    "Evolução de exemplo gerada por populate_demo_relations. "
                    "Paciente relatou melhora na adesão às sessões."
                ),
                session_date=date.today() - timedelta(days=random.randint(1, 7)),  # nosec B311
            )

            PerformanceReview.objects.create(
                student=aluno,
                teacher=aluno.current_advisor,
                content=(
                    "Feedback de exemplo: boa condução clínica, atenção ao "
                    "registro de evolução e à postura ética em sessão."
                ),
            )
            criados_atendimento += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{criados_triagem} paciente(s) em triagem e "
                f"{criados_atendimento} em atendimento "
                "(com prontuário e feedback) criados."
                f"{atividades_criadas} atividade(s) de exemplo criada(s)."
            )
        )
