from django.conf import settings
from django.db import models
from core.managers import CustomUserManager
from core.models import CustomUser
from core.permissions import BusinessRulesMixin, RoleScopedQuerySet
from students.models import Student
from teacher.models import Teacher

Role = CustomUser.Role


class PatientQuerySet(RoleScopedQuerySet):
    def visible_to(self, user):
        if not user.is_authenticated:
            return self.none()

        role = user.role
        if user.is_superuser or role in (Role.SUPERVISOR, Role.ADMIN):
            return self
        if role == Role.PROFESSOR:
            return self.filter(responsible_student__current_advisor_id=user.pk)
        if role == Role.ALUNO:
            return self.filter(responsible_student_id=user.pk)
        if role == Role.PACIENTE:
            return self.filter(pk=user.pk)
        return self.none()


class Patient(BusinessRulesMixin, CustomUser):
    responsible_student = models.ForeignKey(
        Student,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="patients",
        verbose_name="Aluno responsável",
    )

    responsible_teacher = models.ForeignKey(
        Teacher,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="referred_patients",
        verbose_name="Professor responsável",
    )

    active_treatment = models.BooleanField(
        default=True,
        verbose_name="Em atendimento ativo",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    objects = CustomUserManager.from_queryset(PatientQuerySet)()

    REGISTRATION_FIELDS = ("nome_completo", "cpf") + CustomUser.ADDRESS_FIELDS

    CREATABLE_BY = (Role.ADMIN,)
    EDITABLE_FIELDS = {
        Role.SUPERVISOR: ("responsible_teacher",),
        Role.PROFESSOR: ("responsible_teacher",),
        Role.ADMIN: REGISTRATION_FIELDS,
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
        if user.is_superuser or role == Role.SUPERVISOR:
            return self
        if role == Role.PROFESSOR:
            return self.filter(student__current_advisor_id=user.pk)
        if role == Role.ALUNO:
            return self.filter(student_id=user.pk)
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
            return patient.active_treatment and patient.responsible_student_id == user.pk
        return True

    def editable_fields_for(self, user):
        fields = super().editable_fields_for(user)
        if user.is_authenticated and user.role == Role.SUPERVISOR and not self.pending_confirmation:
            return ()
        return fields

    @property
    def pending_confirmation(self):
        return self.confirmed_at is None

    def __str__(self):
        return f"Evolução de {self.patient} em {self.session_date}"


class AppointmentQuerySet(RoleScopedQuerySet):
    def visible_to(self, user):
        if not user.is_authenticated:
            return self.none()

        role = user.role
        if user.is_superuser or role in (Role.SUPERVISOR, Role.ADMIN):
            return self
        if role == Role.PROFESSOR:
            return self.filter(assigned_student__current_advisor_id=user.pk)
        if role == Role.ALUNO:
            return self.filter(assigned_student_id=user.pk)
        if role == Role.PACIENTE:
            return self.filter(patient_id=user.pk)
        return self.none()


class Appointment(BusinessRulesMixin, models.Model):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="appointments",
        verbose_name="Paciente",
    )

    assigned_student = models.ForeignKey(
        Student,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="appointments",
        verbose_name="Aluno que atende",
    )

    scheduled_at = models.DateTimeField(verbose_name="Data e hora")

    notes = models.TextField(blank=True, verbose_name="Observações")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    objects = AppointmentQuerySet.as_manager()

    CREATABLE_BY = (Role.PROFESSOR, Role.ADMIN)
    EDITABLE_FIELDS = {
        Role.PROFESSOR: ("assigned_student",),
        Role.ADMIN: ("scheduled_at", "notes", "assigned_student"),
    }
    DELETABLE_BY = ()

    class Meta:
        verbose_name = "Agendamento"
        verbose_name_plural = "Agendamentos"
        ordering = ["scheduled_at"]

    def __str__(self):
        return f"{self.patient} em {self.scheduled_at:%d/%m/%Y %H:%M}"
