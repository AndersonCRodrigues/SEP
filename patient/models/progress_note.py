from django.conf import settings
from django.db import models
from areas.models import AreaActing
from core.models import CustomUser
from core.permissions import BusinessRulesMixin, RoleScopedQuerySet
from students.models import Student, with_open_case
from .patient import Patient

Role = CustomUser.Role


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
            return self.filter(with_open_case("patient__", student_id=user.pk))
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
            return patient.active_treatment and patient.is_treated_by(user)
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
