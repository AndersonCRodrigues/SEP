import os
from datetime import date, datetime, time, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from areas.models import AreaActing
from core.models import CustomUser
from documents.models import AttendanceCertificate, InternshipDeclaration
from patient.models import Patient
from scheduling.models import Appointment, Room, RoomBooking
from students.models import Student, CaseAssignment
from teacher.models import Teacher
from django.db import transaction

ROOMS = 7
UNUSABLE_ROOMS = (Room.Status.MAINTENANCE, Room.Status.INACTIVE)
OCCUPIED_ROOMS = 5
APPOINTMENTS_TODAY = 18
CERTIFICATES_TODAY = 6
PENDING_DECLARATIONS = 2
INTERNSHIP_DECLARATIONS = 2
DAYS_WITH_SCHEDULE = (3, 7, 12, 16, 19, 23, 27)

WEEK_SCHEDULE = (
    (-1, 14, Appointment.Status.ATTENDED),
    (-1, 15, Appointment.Status.PATIENT_NO_SHOW),
    (-2, 10, Appointment.Status.ATTENDED),
    (-3, 16, Appointment.Status.CANCELLED),
    (1, 9, Appointment.Status.SCHEDULED),
    (1, 10, Appointment.Status.SCHEDULED),
)

HOURS_BETWEEN_ACTIVITIES = 9


class Command(BaseCommand):
    help = (
        "Cria salas, reservas, atendimentos e atestados para as "
        "telas do Administrativo."
    )

    def add_arguments(self, parser):
       parser.add_argument("--confirmar-base-demo", action="store_true", help="Confirma que a carga será executada em uma base destinada à demonstração.")

    @transaction.atomic
    def handle(self, *args, **options):
        self.created_appointment_ids = []
        self.created_certificate_ids = []

        if os.getenv("NODE_ENV") != "dev":
            self.stdout.write(
                self.style.WARNING(
                    "Ignorado: populate_admin_home só roda com NODE_ENV=dev."
                )
            )
            return
        if not options["confirmar_base_demo"]:
            raise CommandError("Carga não executada. Use --confirmar-base-demo somente em uma base destinada à demonstração.")
        now = timezone.localtime()
        today = now.date()

        administrative = CustomUser.objects.filter(
            role=CustomUser.Role.ADMINISTRATIVO
        ).first()
        teacher = Teacher.objects.filter(role=CustomUser.Role.PROFESSOR).first()
        area = AreaActing.objects.first()

        if not (administrative and teacher and area):
            self.stdout.write(
                self.style.ERROR(
                    "Faltam usuários base. Rode antes: manage.py populate_users"
                )
            )
            return


        students, patients = self.prepare_people(teacher, area)
        if not (students and patients):
            self.stdout.write(
                self.style.ERROR("Sem alunos ou pacientes. Rode populate_users antes.")
            )
            return

        rooms = self.create_rooms()
        self.book(rooms, students, patients, now)
        self.release(rooms, students[0], patients[0], today)
        self.schedule(rooms, students, patients, teacher, now)
        self.schedule_week(rooms, students, patients, teacher, now)
        self.issue(patients, administrative, area, today)
        self.request_declarations(patients, students, administrative, area, today)
        self.spread_over_time(now)

        self.summarize(today, now)

    def prepare_people(self, teacher, area):
        cases = CaseAssignment.objects.open().filter(
            student__stage=Student.Stage.TREATMENT,
            student__current_advisor=teacher,
            patient__flow_status=Patient.FlowStatus.IN_TREATMENT,
            acting_area=area,
        ).select_related("student", "patient").order_by("pk")[:6]

        students = []
        patients = []

        for case in cases:
            students.append(case.student)
            patients.append(case.patient)

        self.stdout.write(f"{len(students)} vínculos ativos selecionados, sem alterações.")
        return students, patients

    def create_rooms(self):
        rooms = []

        for number in range(1, ROOMS + 1):
            room, _ = Room.objects.get_or_create(
                name=f"[DEMO ADM-07] Sala {number}",
                defaults={
                    "room_type": (
                        Room.RoomType.CHILD
                        if number > ROOMS - 2
                        else Room.RoomType.ADULT
                    ),
                    "status": Room.Status.ACTIVE,
                },
            )
            rooms.append(room)

        for number, status in enumerate(
            UNUSABLE_ROOMS,
            start=ROOMS + 1,
        ):
            Room.objects.get_or_create(
                name=f"[DEMO ADM-07] Sala {number}",
                defaults={
                    "room_type": Room.RoomType.ADULT,
                    "status": status,
                },
            )

        self.stdout.write(
            f"{len(rooms)} salas da demonstração disponíveis para a carga."
        )

        return rooms

    def book(self, rooms, students, patients, now):
        window_start = datetime.combine(date.min, (now - RoomBooking.DURATION).time())
        step = timedelta(minutes=50 // OCCUPIED_ROOMS)
        created_count = 0

        for number, room in enumerate(rooms[:OCCUPIED_ROOMS]):
            if not room.is_usable:
                continue

            existing_booking = RoomBooking.objects.filter(
                room=room,
                weekday=now.weekday(),
                end_date__isnull=True,
            ).exists()

            if existing_booking:
                continue

            start = (window_start + step * (number + 1)+ timedelta(minutes=1)).time()

            _, created = RoomBooking.objects.get_or_create(
                room=room,
                weekday=now.weekday(),
                start_time=start,
                end_date__isnull=True,
                defaults={
                    "patient": patients[number % len(patients)],
                    "student": students[number % len(students)],
                },
            )

            if created:
                created_count += 1

        self.stdout.write(f"{created_count} reservas abertas criadas. "
            "Reservas existentes foram preservadas.")

    def release(self, rooms, student, patient, today):
        created_count = 0

        for room, days in zip(rooms[OCCUPIED_ROOMS:], (0, 2)):
            _, created = RoomBooking.objects.get_or_create(
                room=room,
                patient=patient,
                student=student,
                weekday=(today.weekday() + 1) % 6,
                start_time=time(16, 0),
                end_date=today - timedelta(days=days),
            )

            if created:
                created_count += 1

        self.stdout.write(
            f"{created_count} reservas encerradas criadas."
        )

    def schedule(self, rooms, students, patients, teacher, now):
        start = now.replace(hour=8, minute=0, second=0, microsecond=0)
        created_today = 0

        for number in range(APPOINTMENTS_TODAY):
            when = start + timedelta(minutes=50 * number)
            room = rooms[number % OCCUPIED_ROOMS]

            if not room.is_usable:
                continue

            appointment, created = Appointment.objects.get_or_create(
                room=room,
                scheduled_at=when,
                defaults={
                    "patient": patients[number % len(patients)],
                    "assigned_student": students[number % len(students)],
                    "teacher": teacher,
                    "kind": (
                        Appointment.Kind.SESSION
                        if number % 3
                        else Appointment.Kind.SCREENING
                    ),
                    "status": (
                        Appointment.Status.ATTENDED
                        if when < now
                        else Appointment.Status.SCHEDULED
                    ),
                    "duration_minutes": 50,
                },
            )

            if created:
                self.created_appointment_ids.append(appointment.pk)
                created_today += 1

        self.stdout.write(
            f"{created_today} atendimentos criados para hoje."
        )

        created_month = 0

        for number, day in enumerate(DAYS_WITH_SCHEDULE):
            try:
                when = timezone.make_aware(
                    datetime(now.year, now.month, day, 9 + number % 6)
                )
            except ValueError:
                continue

            room = rooms[(number + 3) % len(rooms)]

            if not room.is_usable:
                continue

            appointment, created = Appointment.objects.get_or_create(
                room=room,
                scheduled_at=when,
                defaults={
                    "patient": patients[number % len(patients)],
                    "assigned_student": students[number % len(students)],
                    "teacher": teacher,
                    "duration_minutes": 50,
                },
            )

            if created:
                self.created_appointment_ids.append(appointment.pk)
                created_month += 1

        self.stdout.write(
            f"{created_month} agendamentos criados para o calendário."
        )


    def schedule_week(self, rooms, students, patients, teacher, now):
        created_count = 0

        for number, (offset, hour, status) in enumerate(WEEK_SCHEDULE):
            when = (now + timedelta(days=offset)).replace(hour=hour, minute=30, second=0, microsecond=0)
            room = rooms[number % len(rooms)]

            if not room.is_usable:
                continue

            appointment, created = Appointment.objects.get_or_create(
                room=room, scheduled_at=when,
                defaults={
                    "patient": patients[number % len(patients)],
                    "assigned_student": students[number % len(students)],
                    "teacher": teacher,
                    "status": status,
                    "duration_minutes": 50,
                },
            )

            if created:
                self.created_appointment_ids.append(appointment.pk)
                created_count += 1

        self.stdout.write(f"{created_count} atendimentos criados para a agenda da semana.")

    def issue(self, patients, administrative, area, today):
        created_count = 0

        for number in range(CERTIFICATES_TODAY):
            document, created = AttendanceCertificate.objects.get_or_create(
                patient=patients[number % len(patients)],
                student=None,
                content=(
                    f"[DEMO ADM-07:issued:{today}:{number}] "
                    "Compareceu ao atendimento no Serviço Escola de Psicologia."
                ),
                defaults={
                    "kind": (
                        AttendanceCertificate.Kind.DECLARATION
                        if number % 2
                        else AttendanceCertificate.Kind.MEDICAL_CERTIFICATE
                    ),
                    "status": AttendanceCertificate.Status.ISSUED,
                    "issued_at": today,
                    "issued_by": administrative,
                    "acting_area": area,
                },
            )

            if created:
                self.created_certificate_ids.append(document.pk)
                created_count += 1

        self.stdout.write(
            f"{created_count} documentos de demonstração emitidos para hoje."
        )

    def request_declarations(self, patients, students, administrative, area, today):
        for number in range(PENDING_DECLARATIONS):
            document = AttendanceCertificate.objects.create(
                patient=patients[number % len(patients)],
                kind=AttendanceCertificate.Kind.DECLARATION,
                content="Aguardando emissão da declaração de comparecimento.",
                acting_area=area,
            )
            self.created_certificate_ids.append(document.pk)

        for number, student in enumerate(students[:INTERNSHIP_DECLARATIONS]):
            issued = number == 0
            InternshipDeclaration.objects.create(
                student=student,
                content="Horas de estágio cumpridas no período.",
                start_date=today - timedelta(days=30),
                end_date=today,
                total_minutes=60 * 40,
                status=(
                    InternshipDeclaration.Status.ISSUED
                    if issued
                    else InternshipDeclaration.Status.PENDING
                ),
                issued_at=today if issued else None,
                issued_by=administrative if issued else None,
            )

        document = AttendanceCertificate.objects.create(
            student=students[0],
            kind=AttendanceCertificate.Kind.MEDICAL_CERTIFICATE,
            content="Compareceu ao atendimento no Serviço Escola de Psicologia.",
            status=AttendanceCertificate.Status.ISSUED,
            issued_at=today,
            issued_by=administrative,
            acting_area=area,
        )
        self.created_certificate_ids.append(document.pk)

        self.stdout.write(
            f"{PENDING_DECLARATIONS} declaracoes pendentes de paciente, "
            f"{INTERNSHIP_DECLARATIONS} de estagio e 1 atestado de aluno."
        )

    def spread_over_time(self, now):
        for number, appointment_id in enumerate(self.created_appointment_ids):
            Appointment.objects.filter(pk=appointment_id).update(created_at=now - timedelta(days=number % 6, hours=number % 7))

        for number, certificate_id in enumerate(self.created_certificate_ids):
            AttendanceCertificate.objects.filter(pk=certificate_id).update(created_at=now - timedelta(hours=number * HOURS_BETWEEN_ACTIVITIES))

        self.stdout.write("Datas ajustadas somente nos registros criados nesta execução.")

    def summarize(self, today, now):
        occupied = (
            RoomBooking.objects.occupying(now)
            .filter(room__isnull=False)
            .values("room")
            .distinct()
            .count()
        )
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Como a página inicial vai exibir:"))
        self.stdout.write(
            f"  Salas ocupadas        : {occupied}/{Room.objects.usable().count()}"
        )
        self.stdout.write(
            "  Atendimentos hoje     : "
            f"{Appointment.objects.filter(scheduled_at__date=today).count()}"
        )
        pending = (
            AttendanceCertificate.objects.filter(
                kind=AttendanceCertificate.Kind.DECLARATION,
                status=AttendanceCertificate.Status.PENDING,
            ).count()
            + InternshipDeclaration.objects.filter(
                status=InternshipDeclaration.Status.PENDING
            ).count()
        )
        self.stdout.write(f"  Declarações pendentes : {pending}")
        self.stdout.write(
            "  Atestados emitidos    : "
            f"{AttendanceCertificate.objects.filter(issued_at=today).count()}"
        )
