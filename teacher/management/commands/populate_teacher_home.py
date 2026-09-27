import os
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from areas.models import AreaActing
from core.constants import TriageStatus
from core.models import CustomUser
from core.utils import sincronizar_grupo
from patient.models import Patient, ProgressNote
from students.models import CaseAssignment, Student
from teacher.models import Teacher
from triage.models import TriageRecord

DEMO_EMAIL = "professor.demo@teste.com"
DEMO_PASSWORD = "Professor@123"  # nosec B105

STUDENTS = (
    ("Marina", "Costa", "aluno.prof1@teste.com"),
    ("Pedro", "Alves", "aluno.prof2@teste.com"),
    ("João", "Ribeiro", "aluno.prof3@teste.com"),
)

QUEUE = (
    ("José", "Santos", 1),
    ("Camila", "Duarte", 2),
    ("Rafael", "Nunes", 3),
)

ASSIGNED = (
    ("Lucas", "Prado", 4, 0),
    ("Bianca", "Moraes", 5, 1),
)

NOTES = (
    "Primeira sessão: vínculo estabelecido e queixa principal confirmada.",
    "Paciente relatou melhora do sono e retomada das atividades de estudo.",
    "Trabalhados recursos de enfrentamento; tarefa combinada para a próxima sessão.",
)

ADDRESS = dict(
    telefone="21999990000",
    logradouro="Rua da Demonstração",
    numero="10",
    bairro="Centro",
    cidade="Maricá",
    estado="RJ",
    cep="24900-000",
)


def valid_cpf():
    digits = [random.randint(0, 9) for _ in range(9)]  # nosec B311
    for size in (10, 11):
        remainder = 11 - sum(d * w for d, w in zip(digits, range(size, 1, -1))) % 11
        digits.append(0 if remainder >= 10 else remainder)
    return "".join(map(str, digits))


class Command(BaseCommand):
    help = (
        "Cria um professor de demonstração com pacientes encaminhados pela "
        "coordenação, alunos orientados e prontuários em evolução."
    )

    def handle(self, *args, **options):
        if os.getenv("NODE_ENV") != "dev":
            self.stdout.write(
                self.style.WARNING(
                    "Ignorado: populate_teacher_home só roda com NODE_ENV=dev."
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

        coordenador = CustomUser.objects.filter(
            role=CustomUser.Role.SUPERVISOR
        ).first()

        with transaction.atomic():
            professor = self.demo_teacher(area)
            self.clean()
            alunos = self.students(professor)
            self.queue(professor, alunos, coordenador)
            casos = self.assigned(professor, alunos, area, coordenador)
            self.records(casos, coordenador)

        self.summarize(alunos, coordenador)

    def demo_teacher(self, area):
        professor = Teacher.objects.filter(email=DEMO_EMAIL).first()
        if professor is None:
            professor = Teacher(
                email=DEMO_EMAIL,
                first_name="Renata",
                last_name="Alves",
                cpf=valid_cpf(),
                crp="05/10001",
                role=CustomUser.Role.PROFESSOR,
                **ADDRESS,
            )
            professor.set_password(DEMO_PASSWORD)

        professor.role = CustomUser.Role.PROFESSOR
        professor.save()
        sincronizar_grupo(professor)
        professor.acting_areas.set([area])

        self.stdout.write(f"Professor de demonstração pronto: {professor}.")
        return professor

    @staticmethod
    def clean():
        pacientes = Patient.objects.filter(email__startswith="paciente.prof")

        ProgressNote.objects.filter(patient__in=pacientes).delete()
        TriageRecord.objects.filter(patient__in=pacientes).delete()
        CaseAssignment.objects.filter(patient__in=pacientes).delete()
        for paciente in pacientes:
            paciente.responsible_teachers.clear()

    def students(self, professor):
        alunos = []
        for first_name, last_name, email in STUDENTS:
            aluno = Student.objects.filter(email=email).first()
            if aluno is None:
                aluno = Student(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    cpf=valid_cpf(),
                    matricula=f"P{random.randint(100000, 999999)}",  # nosec B311
                    **ADDRESS,
                )
                aluno.set_password(DEMO_PASSWORD)

            aluno.current_advisor = professor
            aluno.stage = Student.Stage.TREATMENT
            aluno.save()
            sincronizar_grupo(aluno)
            alunos.append(aluno)

        self.stdout.write(f"{len(alunos)} alunos orientados por {professor}.")
        return alunos

    def patient(self, first_name, last_name, numero):
        email = f"paciente.prof{numero}@teste.com"
        paciente = Patient.objects.filter(email=email).first()
        if paciente is None:
            paciente = Patient(
                email=email,
                first_name=first_name,
                last_name=last_name,
                cpf=valid_cpf(),
                **ADDRESS,
            )
            paciente.set_password(DEMO_PASSWORD)
            paciente.save()

        Patient.objects.filter(pk=paciente.pk).update(
            flow_status=Patient.FlowStatus.AWAITING_TRIAGE
        )
        paciente.refresh_from_db()
        return paciente

    def queue(self, professor, alunos, coordenador):
        fila = []
        for indice, (first_name, last_name, numero) in enumerate(QUEUE):
            paciente = self.patient(first_name, last_name, numero)
            autor = alunos[indice % len(alunos)]
            fila.append(self.refer(paciente, autor, professor, coordenador))

        self.stdout.write(
            f"{len(fila)} pacientes encaminhados pela coordenação, "
            "aguardando o professor."
        )
        return fila

    def assigned(self, professor, alunos, area, coordenador):
        casos = []
        for first_name, last_name, numero, indice in ASSIGNED:
            aluno = alunos[indice]
            paciente = self.patient(first_name, last_name, numero)
            self.refer(paciente, aluno, professor, coordenador)
            casos.append(
                CaseAssignment.objects.assign(aluno, paciente, acting_area=area)
            )

        nomes = ", ".join(caso.student.get_full_name() for caso in casos)
        self.stdout.write(f"{len(casos)} pacientes já em atendimento com {nomes}.")
        return casos

    def records(self, casos, coordenador):
        hoje = timezone.localdate()
        agora = timezone.now()
        total = 0
        confirmadas = 0

        for indice, caso in enumerate(casos):
            for ordem, conteudo in enumerate(NOTES):
                dias = 7 * (len(NOTES) - ordem - 1) + indice
                nota = ProgressNote.objects.create(
                    patient=caso.patient,
                    student=caso.student,
                    acting_area=caso.acting_area,
                    content=conteudo,
                    session_date=hoje - timedelta(days=dias),
                )
                ProgressNote.objects.filter(pk=nota.pk).update(
                    created_at=agora - timedelta(days=dias, hours=indice)
                )

                if ordem == 0 and coordenador is not None:
                    ProgressNote.objects.filter(pk=nota.pk).update(
                        confirmed_by=coordenador,
                        confirmed_at=agora - timedelta(days=dias - 1),
                    )
                    confirmadas += 1

                total += 1

        self.stdout.write(
            f"{total} evoluções no prontuário, {total - confirmadas} aguardando "
            "confirmação."
        )

    @staticmethod
    def refer(paciente, autor, professor, coordenador):
        record = TriageRecord.objects.create(
            patient=paciente,
            student_author=autor,
            chief_complaint="Ficha de demonstração concluída pelo aluno.",
        )
        record.submit(autor)

        paciente.responsible_teachers.set([professor])
        record.status = TriageStatus.REFERRED
        record.closed_by = coordenador
        record.closed_at = timezone.now()
        record.save()
        paciente.refresh_from_db()
        return record

    def summarize(self, alunos, coordenador):
        nomes = ", ".join(aluno.get_full_name() for aluno in alunos)

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS("Entre como o professor de demonstração:")
        )
        self.stdout.write(f"  E-mail : {DEMO_EMAIL}")
        self.stdout.write(f"  Senha  : {DEMO_PASSWORD}")
        self.stdout.write("  Telas  : /teacher/, encaminhamentos, prontuarios,")
        self.stdout.write("           presenca e avaliacoes")
        self.stdout.write(f"  Alunos : {nomes}")
        self.stdout.write(f"  Senha dos alunos: {DEMO_PASSWORD}")

        if coordenador is None:
            self.stdout.write(
                self.style.WARNING(
                    "Sem Coordenador no banco: as triagens ficaram sem quem "
                    "encaminhou e nenhuma evolução nasceu confirmada. Rode "
                    "manage.py populate_users para ter um."
                )
            )
