import os
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from areas.models import AreaActing
from core.models import CustomUser
from core.utils import sincronizar_grupo
from patient.models import Patient, ProgressNote
from scheduling.models import Appointment
from students.models import CaseAssignment, Student
from teacher.models import Teacher
from triage.models import TriageFeedback, TriageRecord

DEMO_EMAIL = "aluno.demo@teste.com"
EMPTY_EMAIL = "aluno.vazio@teste.com"
DEMO_PASSWORD = "Aluno@123"  # nosec B105
DEMO_REGISTRATION = "20260001"

SESSION_HOUR = 15
CASES = (
    ("Ana", "Beatriz", "paciente.ana@teste.com", 0),
    ("Rafael", "Nunes", "paciente.rafael@teste.com", 10),
    ("Lucas", "Prado", "paciente.lucas@teste.com", 25),
)
TRIAGE_PATIENT = ("José", "Santos", "paciente.jose@teste.com")

HISTORY = (
    (2, Appointment.Status.ATTENDED),
    (5, Appointment.Status.STUDENT_NO_SHOW),
    (9, Appointment.Status.CANCELLED),
)
UPCOMING_DAYS = (1, 6, 13)

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
        "Cria um aluno de demonstração com pacientes, evoluções, triagem e feedbacks."
    )

    def handle(self, *args, **options):
        if os.getenv("NODE_ENV") != "dev":
            self.stdout.write(
                self.style.WARNING(
                    "Ignorado: populate_student_home só roda com NODE_ENV=dev."
                )
            )
            return

        teacher = Teacher.objects.filter(role=CustomUser.Role.PROFESSOR).first()
        supervisor = (
            Teacher.objects.filter(role=CustomUser.Role.SUPERVISOR).first() or teacher
        )
        area = AreaActing.objects.first()

        if not (teacher and area):
            self.stdout.write(
                self.style.ERROR(
                    "Faltam usuários base. Rode antes: manage.py populate_users"
                )
            )
            return

        with transaction.atomic():
            student = self.demo_student(teacher)
            self.clean(student)
            patients = self.cases(student, area)
            self.notes(student, patients, area, supervisor)
            self.sessions(student, teacher, patients[0])
            triage = self.triage(student, supervisor)
            self.empty_student(teacher)

        self.summarize(student, triage)

    def demo_student(self, teacher):
        student = Student.objects.filter(email=DEMO_EMAIL).first()
        if student is None:
            student = Student(
                email=DEMO_EMAIL,
                first_name="Marina",
                last_name="Costa",
                cpf=valid_cpf(),
                matricula=self.free_registration(),
                **ADDRESS,
            )
            student.set_password(DEMO_PASSWORD)

        student.current_advisor = teacher
        student.stage = Student.Stage.TREATMENT
        student.save()
        sincronizar_grupo(student)
        self.stdout.write(f"Aluno de demonstração pronto: {student}.")
        return student

    def empty_student(self, teacher):
        student = Student.objects.filter(email=EMPTY_EMAIL).first()
        if student is None:
            student = Student(
                email=EMPTY_EMAIL,
                first_name="Bruno",
                last_name="Almeida",
                cpf=valid_cpf(),
                matricula=self.free_registration(),
                **ADDRESS,
            )
            student.set_password(DEMO_PASSWORD)

        student.current_advisor = teacher
        student.stage = Student.Stage.TRIAGE
        student.save()
        sincronizar_grupo(student)
        self.clean(student)
        self.stdout.write("Aluno sem dado nenhum pronto, para ver os estados vazios.")
        return student

    @staticmethod
    def free_registration():
        registration = DEMO_REGISTRATION
        suffix = 0
        while CustomUser.objects.filter(matricula=registration).exists():
            suffix += 1
            registration = f"{DEMO_REGISTRATION}{suffix}"
        return registration

    @staticmethod
    def clean(student):
        Appointment.objects.filter(assigned_student=student).delete()
        ProgressNote.objects.filter(student=student).delete()
        CaseAssignment.objects.filter(student=student).delete()
        TriageFeedback.objects.filter(triage__student_author=student).delete()
        TriageRecord.objects.filter(student_author=student).delete()

    def patient(self, first_name, last_name, email):
        person = Patient.objects.filter(email=email).first()
        if person is None:
            person = Patient(
                email=email,
                first_name=first_name,
                last_name=last_name,
                cpf=valid_cpf(),
                **ADDRESS,
            )
            person.set_password(DEMO_PASSWORD)
            person.save()

        Patient.objects.filter(pk=person.pk).update(
            flow_status=Patient.FlowStatus.REFERRED
        )
        person.refresh_from_db()
        return person

    def cases(self, student, area):
        today = timezone.localdate()
        patients = []

        for first_name, last_name, email, days_ago in CASES:
            person = self.patient(first_name, last_name, email)
            case = CaseAssignment.objects.assign(student, person, acting_area=area)
            if days_ago:
                CaseAssignment.objects.filter(pk=case.pk).update(
                    start_date=today - timedelta(days=days_ago)
                )
            patients.append(person)

        self.stdout.write(
            f"{len(patients)} encaminhamentos abertos, sendo 1 recebido hoje."
        )
        return patients

    def notes(self, student, patients, area, supervisor):
        confirmed, pending, _ = patients

        ProgressNote.objects.create(
            patient=confirmed,
            student=student,
            acting_area=area,
            content="Evolução revisada pela coordenação.",
            session_date=timezone.localdate() - timedelta(days=2),
            confirmed_by=supervisor,
            confirmed_at=timezone.now(),
        )

        note = ProgressNote.objects.create(
            patient=pending,
            student=student,
            acting_area=area,
            content="Evolução aguardando revisão.",
            session_date=timezone.localdate() - timedelta(days=3),
        )
        ProgressNote.objects.filter(pk=note.pk).update(
            updated_at=timezone.now() - timedelta(days=3)
        )

        self.stdout.write(
            "Prontuários: 1 revisado, 1 pendente e 1 paciente sem evolução."
        )

    def sessions(self, student, teacher, patient):
        today = timezone.localtime().replace(
            hour=SESSION_HOUR, minute=0, second=0, microsecond=0
        )

        for days, status in HISTORY:
            Appointment.objects.create(
                patient=patient,
                assigned_student=student,
                teacher=teacher,
                status=status,
                scheduled_at=today - timedelta(days=days),
            )

        for days in UPCOMING_DAYS:
            Appointment.objects.create(
                patient=patient,
                assigned_student=student,
                teacher=teacher,
                scheduled_at=today + timedelta(days=days),
            )

        self.stdout.write(
            f"{len(HISTORY)} atendimentos passados, com 1 falta do aluno, "
            f"e {len(UPCOMING_DAYS)} no calendário."
        )

    def triage(self, student, supervisor):
        first_name, last_name, email = TRIAGE_PATIENT
        person = self.patient(first_name, last_name, email)
        Patient.objects.filter(pk=person.pk).update(flow_status="")
        person.refresh_from_db()

        record = TriageRecord.objects.create(
            patient=person,
            student_author=student,
            chief_complaint="Ficha de demonstração enviada pelo aluno.",
        )
        record.submit(student)
        self.feedbacks(record, supervisor)
        self.stdout.write("Triagem enviada e 3 feedbacks recebidos.")
        return record

    @staticmethod
    def feedbacks(record, supervisor):
        now = timezone.now()
        TriageFeedback.objects.create(
            triage=record, author=supervisor, content="Parecer recebido agora."
        )

        old = TriageFeedback.objects.create(
            triage=record, author=supervisor, content="Parecer já lido."
        )
        TriageFeedback.objects.filter(pk=old.pk).update(
            created_at=now - timedelta(days=4), updated_at=now - timedelta(days=4)
        )

        edited = TriageFeedback.objects.create(
            triage=record, author=supervisor, content="Parecer revisado depois."
        )
        TriageFeedback.objects.filter(pk=edited.pk).update(
            created_at=now - timedelta(days=2), updated_at=now - timedelta(days=1)
        )

    def summarize(self, student, triage):
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Entre como o aluno de demonstração:"))
        self.stdout.write(f"  E-mail  : {DEMO_EMAIL}")
        self.stdout.write(f"  Senha   : {DEMO_PASSWORD}")
        self.stdout.write(f"  Pacientes: {student.open_cases.count()}")
        self.stdout.write(
            f"  Triagem concluída: /students/triagens/{triage.pk}/concluida/"
        )
        self.stdout.write("")
        self.stdout.write("Para ver as telas vazias, entre como:")
        self.stdout.write(f"  E-mail  : {EMPTY_EMAIL}")
        self.stdout.write(f"  Senha   : {DEMO_PASSWORD}")
