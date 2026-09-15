import os
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from areas.models import AreaActing
from core.constants import TriageStatus
from core.models import CustomUser
from patient.models import Patient
from scheduling.models import Appointment, AppointmentRequest
from students.models import CaseAssignment, Student
from teacher.models import Teacher
from triage.models import TriageRecord

DEMO_EMAIL = "paciente.demo@teste.com"
DEMO_PASSWORD = "Paciente@123"
SESSION_HOUR = 14
TRIAGE_DAYS_AGO = 60
OLD_TRIAGE_DAYS_AGO = 400

HISTORY = (
    (7, Appointment.Status.ATTENDED),
    (14, Appointment.Status.ATTENDED),
    (21, Appointment.Status.PATIENT_NO_SHOW),
    (28, Appointment.Status.ATTENDED),
)

UPCOMING_WEEKS = (0, 1, 2, 3)


def valid_cpf():
    digits = [random.randint(0, 9) for _ in range(9)]
    for size in (10, 11):
        remainder = 11 - sum(d * w for d, w in zip(digits, range(size, 1, -1))) % 11
        digits.append(0 if remainder >= 10 else remainder)
    return "".join(map(str, digits))


class Command(BaseCommand):
    help = "Cria um paciente de demonstração com sessões e triagem para as telas do Paciente."

    def handle(self, *args, **options):
        if os.getenv("NODE_ENV") != "dev":
            self.stdout.write(
                self.style.WARNING(
                    "Ignorado: populate_patient_home só roda com NODE_ENV=dev."
                )
            )
            return

        student = (
            Student.objects.filter(current_advisor__isnull=False).first()
            or Student.objects.first()
        )
        teacher = Teacher.objects.filter(role=CustomUser.Role.PROFESSOR).first()
        supervisor = CustomUser.objects.filter(role=CustomUser.Role.SUPERVISOR).first()
        administrative = CustomUser.objects.filter(
            role=CustomUser.Role.ADMINISTRATIVO
        ).first()
        area = AreaActing.objects.first()

        if not (student and teacher and area):
            self.stdout.write(
                self.style.ERROR(
                    "Faltam usuários base. Rode antes: manage.py populate_users"
                )
            )
            return

        with transaction.atomic():
            patient = self.demo_patient()
            self.prepare_student(student, teacher)
            self.triage(patient, student, supervisor or teacher, teacher, area)
            self.sessions(patient, student, teacher)
            self.requests(patient, administrative)

        self.summarize(patient)

    def demo_patient(self):
        patient = Patient.objects.filter(email=DEMO_EMAIL).first()
        if patient is None:
            patient = Patient(
                email=DEMO_EMAIL,
                first_name="Paciente",
                last_name="Demonstração",
                cpf=valid_cpf(),
                telefone="21999990000",
                logradouro="Rua da Demonstração",
                numero="10",
                bairro="Centro",
                cidade="Maricá",
                estado="RJ",
                cep="24900-000",
            )
            patient.set_password(DEMO_PASSWORD)
            patient.save()

        AppointmentRequest.objects.filter(patient=patient).delete()
        Appointment.objects.filter(patient=patient).delete()
        CaseAssignment.objects.filter(patient=patient).delete()
        TriageRecord.objects.filter(patient=patient).delete()
        patient.responsible_teachers.clear()
        Patient.objects.filter(pk=patient.pk).update(flow_status="")
        patient.refresh_from_db()
        self.stdout.write(f"Paciente de demonstração pronto: {patient}.")
        return patient

    @staticmethod
    def prepare_student(student, teacher):
        if not student.current_advisor_id:
            student.current_advisor = teacher
        student.stage = Student.Stage.TREATMENT
        student.save()

    def triage(self, patient, student, referred_by, teacher, area):
        for status, days_ago in (
            (TriageStatus.CLOSED, OLD_TRIAGE_DAYS_AGO),
            (TriageStatus.REFERRED, TRIAGE_DAYS_AGO),
        ):
            record = TriageRecord.objects.create(
                patient=patient,
                student_author=student,
                chief_complaint="Registro de demonstração.",
            )
            closed_at = timezone.now() - timedelta(days=days_ago)
            record.status = status
            record.closed_by = referred_by
            record.closed_at = closed_at
            record.save()
            TriageRecord.objects.filter(pk=record.pk).update(
                created_at=closed_at - timedelta(days=2)
            )

        patient.responsible_teachers.add(teacher)
        CaseAssignment.objects.assign(student, patient, acting_area=area)
        self.stdout.write(
            "Triagem antiga encerrada, triagem atual encaminhada e aluno designado."
        )

    def sessions(self, patient, student, teacher):
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

        upcoming = [
            Appointment.objects.create(
                patient=patient,
                assigned_student=student,
                teacher=teacher,
                scheduled_at=today + timedelta(weeks=weeks),
            )
            for weeks in UPCOMING_WEEKS
        ]
        not_started = next(
            (item for item in upcoming if item.scheduled_at > timezone.now()), None
        )
        if not_started:
            not_started.confirm_presence(teacher)

        self.stdout.write(
            f"{len(HISTORY)} sessões passadas e {len(UPCOMING_WEEKS)} agendadas, "
            "com a presença da próxima confirmada pelo professor."
        )

    def requests(self, patient, administrative):
        if administrative is None:
            self.stdout.write(
                self.style.WARNING("Sem Administrativo: solicitações não criadas.")
            )
            return

        today = timezone.localdate()
        answered = (
            (
                20,
                AppointmentRequest.Period.AFTERNOON,
                True,
                "Horário marcado para as 14h, com o mesmo aluno.",
            ),
            (
                35,
                AppointmentRequest.Period.EVENING,
                False,
                "Não há atendimento à noite nesse dia.",
            ),
        )
        for days_ago, period, accepted, response in answered:
            item = AppointmentRequest.objects.create(
                patient=patient,
                preferred_date=today - timedelta(days=days_ago - 3),
                preferred_period=period,
            )
            item.answer(administrative, accepted=accepted, response=response)
            AppointmentRequest.objects.filter(pk=item.pk).update(
                created_at=timezone.now() - timedelta(days=days_ago)
            )

        self.stdout.write(f"{len(answered)} solicitações de horário já respondidas.")

    def summarize(self, patient):
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Entre como o paciente de demonstração:"))
        self.stdout.write(f"  E-mail : {DEMO_EMAIL}")
        self.stdout.write(f"  Senha  : {DEMO_PASSWORD}")
        self.stdout.write(f"  Sessões: {patient.appointments.count()}")
