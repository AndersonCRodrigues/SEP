from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from core.models import CustomUser
from core.permissions import ALL, BusinessRulesMixin, RoleScopedQuerySet
from students.models import Student
from teacher.models import Teacher
from patient.models import Patient
from .room import Room, RoomBooking

Role = CustomUser.Role


class AppointmentQuerySet(RoleScopedQuerySet):
    VISIBLE_TO = {
        Role.SUPERVISOR: ALL,
        Role.ADMINISTRATIVO: ALL,
        Role.PROFESSOR: lambda u: (
            Q(teacher_id=u.pk) | Q(assigned_student__current_advisor_id=u.pk)
        ),
        Role.ALUNO: lambda u: Q(assigned_student_id=u.pk),
        Role.PACIENTE: lambda u: Q(patient_id=u.pk),
    }


class Appointment(BusinessRulesMixin, models.Model):
    class Kind(models.TextChoices):
        SCREENING = "TR", "Triagem"
        SESSION = "SE", "Consulta"

    class Status(models.TextChoices):
        SCHEDULED = "AG", "Agendado"
        ATTENDED = "RE", "Concluído"
        PATIENT_NO_SHOW = "FP", "Falta do paciente"
        STUDENT_NO_SHOW = "FA", "Falta do aluno"
        CANCELLED = "CA", "Cancelado"

    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="appointments",
        verbose_name="Paciente",
    )

    kind = models.CharField(
        max_length=2,
        choices=Kind.choices,
        default=Kind.SESSION,
        verbose_name="Tipo",
    )

    room = models.ForeignKey(
        Room,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="appointments",
        verbose_name="Sala",
    )

    teacher = models.ForeignKey(
        Teacher,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="allocated_appointments",
        verbose_name="Professor responsável",
    )

    assigned_student = models.ForeignKey(
        Student,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="appointments",
        verbose_name="Aluno que atende",
    )

    status = models.CharField(
        max_length=2,
        choices=Status.choices,
        default=Status.SCHEDULED,
        verbose_name="Situação",
    )

    scheduled_at = models.DateTimeField(verbose_name="Data e hora")

    duration_minutes = models.PositiveIntegerField(
        default=50,
        verbose_name="Duração (minutos)",
    )

    notes = models.TextField(blank=True, verbose_name="Observações")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    objects = AppointmentQuerySet.as_manager()

    CREATABLE_BY = (Role.PROFESSOR, Role.ADMINISTRATIVO)
    EDITABLE_FIELDS = {
        Role.PROFESSOR: ("assigned_student",),
        Role.ADMINISTRATIVO: (
            "scheduled_at",
            "duration_minutes",
            "notes",
            "assigned_student",
            "kind",
            "room",
            "teacher",
            "status",
        ),
    }
    DELETABLE_BY = ()

    @classmethod
    def can_be_created_by(cls, user, teacher=None, **context):
        if not super().can_be_created_by(user):
            return False
        if user.role == Role.PROFESSOR:
            return teacher is not None and teacher.pk == user.pk
        return True

    class Meta:
        verbose_name = "Agendamento"
        verbose_name_plural = "Agendamentos"
        ordering = ["scheduled_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["room", "scheduled_at"],
                condition=Q(room__isnull=False),
                name="room_not_double_booked",
            )
        ]

    def clean(self):
        super().clean()

        if (
            self.kind == self.Kind.SESSION
            and self.assigned_student_id
            and self.assigned_student.in_triage
        ):
            raise ValidationError(
                {"assigned_student": "Aluno em fase de triagem não faz atendimento."}
            )

        if self.room_id and not self.room.is_usable:
            raise ValidationError({"room": "Sala indisponível para agendamento."})

        if not (self.room_id and self.scheduled_at and self.patient_id):
            return

        local = timezone.localtime(self.scheduled_at)
        booking = RoomBooking.objects.open_for(
            self.room_id, local.weekday(), local.time()
        )
        if booking and booking.patient_id != self.patient_id:
            raise ValidationError(
                {"room": f"Sala reservada para {booking.patient} neste horário."}
            )

    def __str__(self):
        return f"{self.get_kind_display()} de {self.patient} em {self.scheduled_at:%d/%m/%Y %H:%M}"
