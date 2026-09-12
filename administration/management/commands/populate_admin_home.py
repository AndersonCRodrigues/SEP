import os
from datetime import date, datetime, time, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from areas.models import AreaActing
from core.models import CustomUser
from documents.models import AttendanceCertificate
from patient.models import Patient
from scheduling.models import Appointment, Room, RoomBooking
from students.models import CaseAssignment, Student
from teacher.models import Teacher

ROOMS = 7
# Sem elas a tela de salas nunca mostraria o laranja nem o cinza.
UNUSABLE_ROOMS = (Room.Status.MAINTENANCE, Room.Status.INACTIVE)
OCCUPIED_ROOMS = 5
APPOINTMENTS_TODAY = 18
CERTIFICATES_TODAY = 6
DAYS_WITH_SCHEDULE = (3, 7, 12, 16, 19, 23, 27)

# Dias vizinhos com situacoes variadas: e o que a Agenda mostra no desenho.
# O minuto 30 mantem esses horarios fora dos usados pelos outros agendamentos,
# que so ocupam o minuto cheio.
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
        parser.add_argument(
            "--manter",
            action="store_true",
            help="Não apaga a demonstração anterior antes de criar a nova.",
        )

    def handle(self, *args, **options):
        if os.getenv("NODE_ENV") != "dev":
            self.stdout.write(
                self.style.WARNING(
                    "Ignorado: populate_admin_home só roda com NODE_ENV=dev."
                )
            )
            return

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

        if not options["manter"]:
            self.clear()

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
        self.spread_over_time(now)

        self.summarize(today, now)

    def clear(self):
        AttendanceCertificate.objects.all().delete()
        Appointment.objects.all().delete()
        RoomBooking.objects.all().delete()
        Room.objects.all().delete()
        self.stdout.write("Demonstração anterior removida.")

    def prepare_people(self, teacher, area):
        students = list(Student.objects.all()[:4])
        for student in students:
            if not student.current_advisor_id:
                student.current_advisor = teacher
            student.stage = Student.Stage.TREATMENT
            student.save()

        patients = list(Patient.objects.all()[:6])
        for student, patient in zip(students, patients):
            if not student.open_cases.exists():
                CaseAssignment.objects.assign(student, patient, acting_area=area)

        self.stdout.write(
            f"{len(students)} alunos e {len(patients)} pacientes prontos."
        )
        return students, patients

    def create_rooms(self):
        """As salas fora de uso entram depois das utilizaveis e ficam fora da
        lista devolvida, para os indicadores da home seguirem sobre 7 salas."""
        rooms = [
            Room.objects.create(
                name=f"Sala {number}",
                room_type=(
                    Room.RoomType.CHILD if number > ROOMS - 2 else Room.RoomType.ADULT
                ),
            )
            for number in range(1, ROOMS + 1)
        ]
        for number, status in enumerate(UNUSABLE_ROOMS, start=ROOMS + 1):
            Room.objects.create(name=f"Sala {number}", status=status)

        self.stdout.write(
            f"{len(rooms)} salas utilizaveis e {len(UNUSABLE_ROOMS)} fora de uso."
        )
        return rooms

    def book(self, rooms, students, patients, now):
        window_start = datetime.combine(date.min, (now - RoomBooking.DURATION).time())
        step = timedelta(minutes=50 // OCCUPIED_ROOMS)

        for number, room in enumerate(rooms[:OCCUPIED_ROOMS]):
            start = (window_start + step * (number + 1) + timedelta(minutes=1)).time()
            RoomBooking.objects.create(
                room=room,
                patient=patients[number % len(patients)],
                student=students[number % len(students)],
                weekday=now.weekday(),
                start_time=start,
            )

        self.stdout.write(f"{OCCUPIED_ROOMS} salas ocupadas neste horário.")

    def release(self, rooms, student, patient, today):
        for room, days in zip(rooms[OCCUPIED_ROOMS:], (0, 2)):
            RoomBooking.objects.create(
                room=room,
                patient=patient,
                student=student,
                weekday=(today.weekday() + 1) % 6,
                start_time=time(16, 0),
                end_date=today - timedelta(days=days),
            )
        self.stdout.write("2 reservas encerradas (viram 'Sala liberada').")

    def schedule(self, rooms, students, patients, teacher, now):
        start = now.replace(hour=8, minute=0, second=0, microsecond=0)
        for number in range(APPOINTMENTS_TODAY):
            when = start + timedelta(minutes=50 * number)
            Appointment.objects.create(
                patient=patients[number % len(patients)],
                assigned_student=students[number % len(students)],
                teacher=teacher,
                # So nas salas reservadas: assim a ocupacao da home continua
                # sendo 5 das 7 salas, como no desenho.
                room=rooms[number % OCCUPIED_ROOMS],
                kind=(
                    Appointment.Kind.SESSION
                    if number % 3
                    else Appointment.Kind.SCREENING
                ),
                status=(
                    Appointment.Status.ATTENDED
                    if when < now
                    else Appointment.Status.SCHEDULED
                ),
                scheduled_at=when,
                duration_minutes=50,
            )
        self.stdout.write(f"{APPOINTMENTS_TODAY} atendimentos hoje.")

        created = 0
        for number, day in enumerate(DAYS_WITH_SCHEDULE):
            try:
                when = timezone.make_aware(
                    datetime(now.year, now.month, day, 9 + number % 6)
                )
            except ValueError:
                continue
            Appointment.objects.create(
                patient=patients[number % len(patients)],
                assigned_student=students[number % len(students)],
                teacher=teacher,
                room=rooms[(number + 3) % len(rooms)],
                scheduled_at=when,
                duration_minutes=50,
            )
            created += 1
        self.stdout.write(f"{created} agendamentos espalhados pelo mês (calendário).")

    def schedule_week(self, rooms, students, patients, teacher, now):
        for number, (offset, hour, status) in enumerate(WEEK_SCHEDULE):
            when = (now + timedelta(days=offset)).replace(
                hour=hour, minute=30, second=0, microsecond=0
            )
            Appointment.objects.create(
                patient=patients[number % len(patients)],
                assigned_student=students[number % len(students)],
                teacher=teacher,
                room=rooms[number % len(rooms)],
                status=status,
                scheduled_at=when,
                duration_minutes=50,
            )
        self.stdout.write(
            f"{len(WEEK_SCHEDULE)} atendimentos nos dias vizinhos (agenda da semana)."
        )

    def issue(self, patients, administrative, area, today):
        for number in range(CERTIFICATES_TODAY):
            AttendanceCertificate.objects.create(
                patient=patients[number % len(patients)],
                kind=(
                    AttendanceCertificate.Kind.DECLARATION
                    if number % 2
                    else AttendanceCertificate.Kind.MEDICAL_CERTIFICATE
                ),
                content="Compareceu ao atendimento no Serviço Escola de Psicologia.",
                issued_at=today,
                issued_by=administrative,
                acting_area=area,
            )
        self.stdout.write(f"{CERTIFICATES_TODAY} atestados emitidos hoje.")

    def spread_over_time(self, now):
        for number, appointment in enumerate(Appointment.objects.order_by("id")):
            Appointment.objects.filter(pk=appointment.pk).update(
                created_at=now - timedelta(days=number % 6, hours=number % 7)
            )
        for number, document in enumerate(AttendanceCertificate.objects.order_by("id")):
            AttendanceCertificate.objects.filter(pk=document.pk).update(
                created_at=now - timedelta(hours=number * HOURS_BETWEEN_ACTIVITIES)
            )
        self.stdout.write("Atividades distribuídas nos últimos dias.")

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
        self.stdout.write("  Declarações pendentes : 0  (sem modelo ainda)")
        self.stdout.write(
            "  Atestados emitidos    : "
            f"{AttendanceCertificate.objects.filter(issued_at=today).count()}"
        )
