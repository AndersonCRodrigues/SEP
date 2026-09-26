import os
import random

from django.core.management.base import BaseCommand
from django.db import transaction
from areas.models import AreaActing
from core.models import CustomUser
from patient.models import Patient
from students.models import Student
from teacher.models import Teacher
from triage.models import TriageFeedback, TriageRecord

DEMO_PREFIX = "paciente.triagem"
DEMO_PASSWORD = "Triagem@123"  # nosec B105

WAITING = (
    ("Helena", "Martins", "AGUARDANDO_TRIAGEM"),
    ("Caio", "Ferraz", "AGUARDANDO_TRIAGEM"),
    ("Iara", "Monteiro", ""),
)
COMPLAINT = "Ficha de demonstração do fluxo de triagem."

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
    help = "Prepara o fluxo de triagem: fila de espera, ficha aberta, enviada e com parecer."

    def handle(self, *args, **options):
        if os.getenv("NODE_ENV") != "dev":
            self.stdout.write(
                self.style.WARNING(
                    "Ignorado: populate_triage_flow só roda com NODE_ENV=dev."
                )
            )
            return

        aluno = (
            Student.objects.filter(email="aluno.demo@teste.com").first()
            or Student.objects.filter(current_advisor__isnull=False).first()
            or Student.objects.first()
        )
        coordenador = Teacher.objects.filter(role=CustomUser.Role.SUPERVISOR).first()
        area = AreaActing.objects.first()

        if not (aluno and coordenador and area):
            self.stdout.write(
                self.style.ERROR(
                    "Faltam usuários base. Rode antes: manage.py populate_users"
                )
            )
            return

        with transaction.atomic():
            self.clean()
            self.waiting_queue()
            aberta = self.open_record(aluno)
            enviada = self.submitted_record(aluno)
            com_parecer = self.reviewed_record(aluno, coordenador)

        self.summarize(aluno, coordenador, aberta, enviada, com_parecer)

    def clean(self):
        pacientes = Patient.objects.filter(email__startswith=DEMO_PREFIX)
        TriageFeedback.objects.filter(triage__patient__in=pacientes).delete()
        TriageRecord.objects.filter(patient__in=pacientes).delete()
        for paciente in pacientes:
            paciente.responsible_teachers.clear()

    def patient(self, first_name, last_name, slug, flow_status):
        email = f"{DEMO_PREFIX}.{slug}@teste.com"
        paciente = Patient.objects.filter(email=email).first()
        if paciente is None:
            paciente = Patient(
                email=email,
                first_name=first_name,
                last_name=last_name,
                cpf=valid_cpf(),
                data_nascimento="1996-04-12",
                **ADDRESS,
            )
            paciente.set_password(DEMO_PASSWORD)
            paciente.save()

        Patient.objects.filter(pk=paciente.pk).update(flow_status=flow_status)
        paciente.refresh_from_db()
        return paciente

    def waiting_queue(self):
        for numero, (first_name, last_name, flow_status) in enumerate(WAITING, start=1):
            self.patient(first_name, last_name, f"espera{numero}", flow_status)

        self.stdout.write(
            f"{len(WAITING)} pacientes aguardando triagem, um deles no estado antigo."
        )

    def open_record(self, aluno):
        paciente = self.patient("Téo", "Barreto", "aberta", "")
        record = TriageRecord.objects.create(
            patient=paciente, student_author=aluno, chief_complaint=COMPLAINT
        )
        self.stdout.write("1 ficha aberta, para o aluno editar e enviar.")
        return record

    def submitted_record(self, aluno):
        paciente = self.patient("Nara", "Vieira", "enviada", "")
        record = TriageRecord.objects.create(
            patient=paciente, student_author=aluno, chief_complaint=COMPLAINT
        )
        record.submit(aluno)
        self.stdout.write("1 ficha enviada, esperando a coordenação analisar.")
        return record

    def reviewed_record(self, aluno, coordenador):
        paciente = self.patient("Ivo", "Sampaio", "parecer", "")
        record = TriageRecord.objects.create(
            patient=paciente, student_author=aluno, chief_complaint=COMPLAINT
        )
        record.submit(aluno)
        TriageFeedback.objects.create(
            triage=record,
            author=coordenador,
            content="Boa condução da entrevista, atenção ao registro do risco.",
        )
        record.finalize_edition(coordenador)
        self.stdout.write("1 ficha com parecer e edição já fechada pela coordenação.")
        return record

    def summarize(self, aluno, coordenador, aberta, enviada, com_parecer):
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Fluxo de triagem pronto para teste:"))
        self.stdout.write(f"  Aluno        : {aluno.email}")
        self.stdout.write(f"  Coordenação  : {coordenador.email}")
        self.stdout.write("")
        self.stdout.write("  Fila de espera   : /triage/fila/ e /students/triagens/")
        self.stdout.write(f"  Ficha aberta     : /triage/student_detail/{aberta.pk}/")
        self.stdout.write(
            f"  Ficha enviada    : /triage/supervisor_detail/{enviada.pk}/"
        )
        self.stdout.write(
            f"  Ficha com parecer: /triage/student_detail/{com_parecer.pk}/"
        )
        self.stdout.write("  Minhas triagens  : /triage/minhas-triagens/")
