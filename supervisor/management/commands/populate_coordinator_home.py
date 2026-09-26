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
from patient.models import Patient
from students.models import CaseAssignment, Student
from teacher.models import Teacher
from triage.models import TriageFeedback, TriageRecord

DEMO_EMAIL = "coordenador.demo@teste.com"
DEMO_PASSWORD = "Coordenador@123"  # nosec B105

TEACHERS = (
    ("Renata", "Alves", "prof.coord1@teste.com", True),
    ("Jorge", "Junior", "prof.coord2@teste.com", True),
    ("Otávio", "Reis", "prof.coord3@teste.com", False),
)
STUDENTS = (
    ("Marina", "Costa", "aluno.coord1@teste.com", 0),
    ("Pedro", "Alves", "aluno.coord2@teste.com", 1),
    ("João", "Ribeiro", "aluno.coord3@teste.com", None),
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
    help = "Cria um coordenador de demonstração com fila de triagens, encaminhamentos e feedbacks."

    def handle(self, *args, **options):
        if os.getenv("NODE_ENV") != "dev":
            self.stdout.write(
                self.style.WARNING(
                    "Ignorado: populate_coordinator_home só roda com NODE_ENV=dev."
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
            coordenador = self.demo_coordinator()
            self.clean()
            professores = self.teachers(area)
            alunos = self.students(professores)
            fila = self.queue(alunos, coordenador)
            self.referrals(fila, professores, alunos, area, coordenador)
            self.feedbacks(fila, coordenador)

        self.summarize(coordenador)

    def demo_coordinator(self):
        coordenador = Teacher.objects.filter(email=DEMO_EMAIL).first()
        if coordenador is None:
            coordenador = Teacher(
                email=DEMO_EMAIL,
                first_name="Sara",
                last_name="Lima",
                cpf=valid_cpf(),
                crp="05/00001",
                role=CustomUser.Role.SUPERVISOR,
                **ADDRESS,
            )
            coordenador.set_password(DEMO_PASSWORD)

        coordenador.role = CustomUser.Role.SUPERVISOR
        coordenador.save()
        sincronizar_grupo(coordenador)
        self.stdout.write(f"Coordenador de demonstração pronto: {coordenador}.")
        return coordenador

    @staticmethod
    def clean():
        emails = [email for _, _, email, _ in TEACHERS]
        emails += [email for _, _, email, _ in STUDENTS]
        pacientes = Patient.objects.filter(email__startswith="paciente.coord")

        TriageFeedback.objects.filter(triage__patient__in=pacientes).delete()
        TriageRecord.objects.filter(patient__in=pacientes).delete()
        CaseAssignment.objects.filter(patient__in=pacientes).delete()
        for paciente in pacientes:
            paciente.responsible_teachers.clear()
        Student.objects.filter(email__in=emails).update(current_advisor=None)

    def teachers(self, area):
        professores = []
        for first_name, last_name, email, _ in TEACHERS:
            professor = Teacher.objects.filter(email=email).first()
            if professor is None:
                professor = Teacher(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    cpf=valid_cpf(),
                    crp=f"05/{random.randint(10000, 99999)}",  # nosec B311
                    role=CustomUser.Role.PROFESSOR,
                    **ADDRESS,
                )
                professor.set_password(DEMO_PASSWORD)
                professor.save()
                sincronizar_grupo(professor)

            professor.acting_areas.set([area])
            professores.append(professor)

        self.stdout.write(f"{len(professores)} professores, 1 deles sem alunos.")
        return professores

    def students(self, professores):
        alunos = []
        for first_name, last_name, email, indice in STUDENTS:
            aluno = Student.objects.filter(email=email).first()
            if aluno is None:
                aluno = Student(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    cpf=valid_cpf(),
                    matricula=f"C{random.randint(100000, 999999)}",  # nosec B311
                    **ADDRESS,
                )
                aluno.set_password(DEMO_PASSWORD)

            aluno.current_advisor = professores[indice] if indice is not None else None
            aluno.stage = Student.Stage.TREATMENT
            aluno.save()
            sincronizar_grupo(aluno)
            alunos.append(aluno)

        self.stdout.write(f"{len(alunos)} alunos, 1 deles sem orientador.")
        return alunos

    def patient(self, first_name, last_name, indice):
        email = f"paciente.coord{indice}@teste.com"
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

    def queue(self, alunos, coordenador):
        marina, pedro, joao = alunos
        agora = timezone.now()

        recente = self.triage(self.patient("José", "Santos", 1), marina)
        atrasada = self.triage(self.patient("Camila", "Duarte", 2), pedro)
        TriageRecord.objects.filter(pk=atrasada.pk).update(
            created_at=agora - timedelta(days=3)
        )

        analisada = self.triage(self.patient("Rafael", "Nunes", 3), joao)
        analisada.status = TriageStatus.CLOSED
        analisada.closed_by = coordenador
        analisada.closed_at = agora - timedelta(days=1)
        analisada.save()

        sem_parecer = self.triage(self.patient("Ana", "Beatriz", 4), marina)
        em_atendimento = self.triage(self.patient("Lucas", "Prado", 5), pedro)

        self.stdout.write(
            "Fila de triagens: 1 para analisar, 1 atrasada e 1 já analisada."
        )
        return {
            "recente": recente,
            "atrasada": atrasada,
            "analisada": analisada,
            "sem_parecer": sem_parecer,
            "em_atendimento": em_atendimento,
        }

    @staticmethod
    def triage(paciente, aluno):
        record = TriageRecord.objects.create(
            patient=paciente,
            student_author=aluno,
            chief_complaint="Ficha de demonstração enviada pelo aluno.",
        )
        record.submit(aluno)
        return record

    def referrals(self, fila, professores, alunos, area, coordenador):
        encaminhada = fila["sem_parecer"]
        encaminhada.patient.responsible_teachers.set(professores[:1])
        encaminhada.status = TriageStatus.REFERRED
        encaminhada.closed_by = coordenador
        encaminhada.closed_at = timezone.now()
        encaminhada.save()

        atendida = fila["em_atendimento"]
        atendida.patient.responsible_teachers.set(professores[1:2])
        atendida.status = TriageStatus.REFERRED
        atendida.closed_by = coordenador
        atendida.closed_at = timezone.now()
        atendida.save()
        atendida.patient.refresh_from_db()
        CaseAssignment.objects.assign(alunos[0], atendida.patient, acting_area=area)

        self.stdout.write("Encaminhamentos: 1 pendente e 1 já em atendimento.")

    def feedbacks(self, fila, coordenador):
        TriageFeedback.objects.create(
            triage=fila["analisada"],
            author=coordenador,
            content="Boa condução da entrevista, atenção ao registro do risco.",
        )
        self.stdout.write("Feedbacks: 1 enviado e 1 a enviar.")

    def summarize(self, coordenador):
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS("Entre como o coordenador de demonstração:")
        )
        self.stdout.write(f"  E-mail : {DEMO_EMAIL}")
        self.stdout.write(f"  Senha  : {DEMO_PASSWORD}")
        self.stdout.write("  Telas  : /supervisor/, professores, alunos, triagens,")
        self.stdout.write("           encaminhamentos e feedbacks")
