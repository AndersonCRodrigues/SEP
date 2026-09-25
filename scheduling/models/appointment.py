from django.conf import settings
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

    class PresenceStatus(models.TextChoices):
        CONFIRMED = "CONFIRMED", "Confirmada"
        AWAITING = "AWAITING", "A confirmar"
        SCHEDULED = "SCHEDULED", "Agendada"

    CONFIRMATION_DAYS = 7

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

    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="confirmed_appointments",
        verbose_name="Presença confirmada por",
    )

    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Presença confirmada em",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    objects = AppointmentQuerySet.as_manager()

    CREATABLE_BY = (Role.PROFESSOR, Role.ADMINISTRATIVO)
    EDITABLE_FIELDS = {
        Role.PROFESSOR: ("assigned_student", "confirmed_by", "confirmed_at"),
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
            ),
            models.CheckConstraint(
                condition=Q(confirmed_by__isnull=True) | Q(confirmed_at__isnull=False),
                name="presence_confirmation_has_date",
            ),
        ]

    def presence_status(self, now=None):
        if self.status != self.Status.SCHEDULED:
            return None
        if self.confirmed_at:
            return self.PresenceStatus.CONFIRMED
        today = timezone.localdate(now) if now else timezone.localdate()
        days_left = (timezone.localdate(self.scheduled_at) - today).days
        if days_left <= self.CONFIRMATION_DAYS:
            return self.PresenceStatus.AWAITING
        return self.PresenceStatus.SCHEDULED

    def can_confirm_presence(self, user):
        if "confirmed_at" not in self.editable_fields_for(user):
            return False
        return type(self).objects.visible_to(user).filter(pk=self.pk).exists()

    def confirm_presence(self, user):
        if not self.can_confirm_presence(user):
            raise ValidationError("Só o professor responsável confirma a presença.")
        if self.status != self.Status.SCHEDULED:
            raise ValidationError(
                "Só um agendamento em aberto tem presença confirmada."
            )
        if self.scheduled_at <= timezone.now():
            raise ValidationError("Este agendamento já começou.")
        if self.confirmed_at:
            return False

        self.confirmed_by_id = user.pk
        self.confirmed_at = timezone.now()
        self.save(update_fields=["confirmed_by", "confirmed_at"])
        return True

    def save(self, *args, **kwargs):
        if self.confirmed_at and not self._state.adding:
            previous = (
                type(self)
                .objects.filter(pk=self.pk)
                .values_list("scheduled_at", flat=True)
                .first()
            )
            if previous is not None and previous != self.scheduled_at:
                self.confirmed_by = None
                self.confirmed_at = None
                update_fields = kwargs.get("update_fields")
                if update_fields is not None:
                    kwargs["update_fields"] = {
                        *update_fields,
                        "confirmed_by",
                        "confirmed_at",
                    }
        super().save(*args, **kwargs)

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
