from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from core.models import CustomUser
from core.permissions import BusinessRulesMixin, RoleScopedQuerySet
from students.models import Student
from .patient import Patient

Role = CustomUser.Role


class RoomQuerySet(RoleScopedQuerySet):
    def visible_to(self, user):
        if not user.is_authenticated:
            return self.none()
        return self

    def usable(self):
        return self.filter(status=Room.Status.ACTIVE)


class Room(BusinessRulesMixin, models.Model):
    class Status(models.TextChoices):
        ACTIVE = "AT", "Ativa"
        MAINTENANCE = "MA", "Em manutenção"
        INACTIVE = "IN", "Inativa"

    class RoomType(models.TextChoices):
        CHILD = "IF", "Infantil"
        ADULT = "AD", "Adulta"

    name = models.CharField(max_length=100, unique=True, verbose_name="Nome")

    room_type = models.CharField(
        max_length=2,
        choices=RoomType.choices,
        default=RoomType.ADULT,
        verbose_name="Tipo de sala",
    )

    status = models.CharField(
        max_length=2,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name="Situação",
    )

    objects = RoomQuerySet.as_manager()

    CREATABLE_BY = (Role.ADMINISTRATIVO,)
    EDITABLE_FIELDS = {Role.ADMINISTRATIVO: ("name", "room_type", "status")}
    DELETABLE_BY = (Role.ADMINISTRATIVO,)

    class Meta:
        verbose_name = "Sala"
        verbose_name_plural = "Salas"
        ordering = ["name"]

    @property
    def is_usable(self):
        return self.status == self.Status.ACTIVE

    def __str__(self):
        return f"{self.name} ({self.get_room_type_display()})"


class RoomBookingQuerySet(RoleScopedQuerySet):
    def visible_to(self, user):
        if not user.is_authenticated:
            return self.none()

        role = user.role
        if role in (Role.SUPERVISOR, Role.ADMINISTRATIVO):
            return self
        if role == Role.PROFESSOR:
            return self.filter(student__current_advisor_id=user.pk)
        if role == Role.ALUNO:
            return self.filter(student_id=user.pk)
        if role == Role.PACIENTE:
            return self.filter(patient_id=user.pk)
        return self.none()

    def open(self):
        return self.filter(end_date__isnull=True)


class RoomBookingManager(models.Manager.from_queryset(RoomBookingQuerySet)):
    def open_for(self, room_id, weekday, start_time):
        return (
            self.open()
            .filter(room_id=room_id, weekday=weekday, start_time=start_time)
            .first()
        )

    def release(self, booking):
        booking.end_date = timezone.localdate()
        booking.save(update_fields=["end_date"])
        return booking


class RoomBooking(BusinessRulesMixin, models.Model):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Segunda-feira"
        TUESDAY = 1, "Terça-feira"
        WEDNESDAY = 2, "Quarta-feira"
        THURSDAY = 3, "Quinta-feira"
        FRIDAY = 4, "Sexta-feira"
        SATURDAY = 5, "Sábado"

    room = models.ForeignKey(
        Room,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="bookings",
        verbose_name="Sala",
    )

    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="bookings",
        verbose_name="Paciente",
    )

    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="bookings",
        verbose_name="Aluno que atende",
    )

    weekday = models.IntegerField(choices=Weekday.choices, verbose_name="Dia da semana")

    start_time = models.TimeField(verbose_name="Horário")

    start_date = models.DateField(auto_now_add=True, verbose_name="Reservada em")

    end_date = models.DateField(null=True, blank=True, verbose_name="Liberada em")

    objects = RoomBookingManager()

    CREATABLE_BY = (Role.ADMINISTRATIVO,)
    EDITABLE_FIELDS = {
        Role.ADMINISTRATIVO: ("room", "weekday", "start_time", "student", "end_date"),
        Role.PROFESSOR: ("student",),
    }
    DELETABLE_BY = ()

    class Meta:
        verbose_name = "Reserva de sala"
        verbose_name_plural = "Reservas de sala"
        ordering = ["weekday", "start_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["room", "weekday", "start_time"],
                condition=Q(end_date__isnull=True),
                name="room_slot_not_double_booked",
            )
        ]

    @property
    def is_open(self):
        return self.end_date is None

    def clean(self):
        super().clean()
        if self.room_id and not self.room.is_usable:
            raise ValidationError({"room": "Sala indisponível para reserva."})

    def __str__(self):
        return (
            f"{self.room} — {self.get_weekday_display()} "
            f"{self.start_time:%H:%M} ({self.student} / {self.patient})"
        )
