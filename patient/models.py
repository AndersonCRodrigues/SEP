from django.conf import settings
from django.db import models
from django.db.models import Q
from areas.models import AreaActing
from core.managers import CustomUserManager
from core.models import CustomUser
from core.permissions import BusinessRulesMixin, RoleScopedQuerySet
from screening.constants import ScreeningStatus
from students.models import Student
from teacher.models import Teacher

Role = CustomUser.Role


class PatientQuerySet(RoleScopedQuerySet):
    def visible_to(self, user):
        if not user.is_authenticated:
            return self.none()

        role = user.role
        if role in (Role.SUPERVISOR, Role.ADMINISTRATIVO):
            return self
        if role == Role.PROFESSOR:
            return self.filter(
                Q(responsible_students__current_advisor_id=user.pk)
                | Q(responsible_teachers=user.pk)
            ).distinct()
        if role == Role.ALUNO:
            return self.filter(
                Q(responsible_students=user.pk, active_treatment=True)
                | Q(
                    screenings__student_id=user.pk,
                    screenings__status=ScreeningStatus.OPEN,
                )
            ).distinct()
        if role == Role.PACIENTE:
            return self.filter(pk=user.pk)
        return self.none()


class Patient(BusinessRulesMixin, CustomUser):
    responsible_teachers = models.ManyToManyField(
        Teacher,
        blank=True,
        related_name="referred_patients",
        verbose_name="Professores responsáveis",
    )

    active_treatment = models.BooleanField(
        default=True,
        verbose_name="Em atendimento ativo",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    objects = CustomUserManager.from_queryset(PatientQuerySet)()

    REGISTRATION_FIELDS = ("nome_completo", "cpf") + CustomUser.ADDRESS_FIELDS

    CREATABLE_BY = (Role.ADMINISTRATIVO, Role.ALUNO)
    EDITABLE_FIELDS = {
        Role.SUPERVISOR: ("responsible_teachers",),
        Role.PROFESSOR: ("responsible_teachers",),
        Role.ADMINISTRATIVO: REGISTRATION_FIELDS,
        Role.PACIENTE: CustomUser.ADDRESS_FIELDS,
    }
    DELETABLE_BY = ()

    class Meta:
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"

    def save(self, *args, **kwargs):
        self.role = CustomUser.Role.PACIENTE
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome_completo


class ProgressNoteQuerySet(RoleScopedQuerySet):
    def visible_to(self, user):
        if not user.is_authenticated:
            return self.none()

        role = user.role
        if role == Role.SUPERVISOR:
            return self
        if role == Role.PROFESSOR:
            return self.filter(student__current_advisor_id=user.pk)
        if role == Role.ALUNO:
            return self.filter(patient__responsible_students=user.pk)
        return self.none()


class ProgressNote(BusinessRulesMixin, models.Model):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="progress_notes",
        verbose_name="Paciente",
    )

    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="progress_notes",
        verbose_name="Aluno responsável",
    )

    acting_area = models.ForeignKey(
        AreaActing,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="progress_notes",
        verbose_name="Área de atuação",
    )

    content = models.TextField(verbose_name="Evolução")

    session_date = models.DateField(verbose_name="Data da sessão")

    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="confirmed_progress_notes",
        verbose_name="Confirmado por",
    )

    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Confirmado em",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    objects = ProgressNoteQuerySet.as_manager()

    CREATABLE_BY = (Role.ALUNO,)
    EDITABLE_FIELDS = {
        Role.SUPERVISOR: ("confirmed_by", "confirmed_at"),
        Role.ALUNO: ("content", "session_date"),
    }
    DELETABLE_BY = ()

    class Meta:
        verbose_name = "Evolução"
        verbose_name_plural = "Evoluções"
        ordering = ["-session_date"]

    @classmethod
    def can_be_created_by(cls, user, patient=None, **context):
        if not super().can_be_created_by(user):
            return False
        if user.role == Role.ALUNO:
            if patient is None:
                return False
            return (
                patient.active_treatment
                and patient.responsible_students.filter(pk=user.pk).exists()
            )
        return True

    def editable_fields_for(self, user):
        fields = super().editable_fields_for(user)
        if (
            user.is_authenticated
            and user.role == Role.SUPERVISOR
            and not self.pending_confirmation
        ):
            return ()
        return fields

    @property
    def pending_confirmation(self):
        return self.confirmed_at is None

    def __str__(self):
        return f"Evolução de {self.patient} em {self.session_date}"


class RoomQuerySet(RoleScopedQuerySet):
    def visible_to(self, user):
        if not user.is_authenticated:
            return self.none()
        return self


class Room(BusinessRulesMixin, models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Nome")

    active = models.BooleanField(default=True, verbose_name="Ativa")

    objects = RoomQuerySet.as_manager()

    CREATABLE_BY = (Role.ADMINISTRATIVO,)
    EDITABLE_FIELDS = {Role.ADMINISTRATIVO: ("name", "active")}
    # Appointment.room usa PROTECT: desativar pelo campo `active`, nao apagar.
    DELETABLE_BY = ()

    class Meta:
        verbose_name = "Sala"
        verbose_name_plural = "Salas"
        ordering = ["name"]

    def __str__(self):
        return self.name


class AppointmentQuerySet(RoleScopedQuerySet):
    def visible_to(self, user):
        if not user.is_authenticated:
            return self.none()

        role = user.role
        if role in (Role.SUPERVISOR, Role.ADMINISTRATIVO):
            return self
        if role == Role.PROFESSOR:
            return self.filter(
                Q(teacher_id=user.pk) | Q(assigned_student__current_advisor_id=user.pk)
            ).distinct()
        if role == Role.ALUNO:
            return self.filter(assigned_student_id=user.pk)
        if role == Role.PACIENTE:
            return self.filter(patient_id=user.pk)
        return self.none()


class Appointment(BusinessRulesMixin, models.Model):
    class Kind(models.TextChoices):
        SCREENING = "TR", "Triagem"
        SESSION = "SE", "Sessão"

    class Status(models.TextChoices):
        SCHEDULED = "AG", "Agendado"
        ATTENDED = "RE", "Realizado"
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
        on_delete=models.PROTECT,
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

    def __str__(self):
        return f"{self.get_kind_display()} de {self.patient} em {self.scheduled_at:%d/%m/%Y %H:%M}"
