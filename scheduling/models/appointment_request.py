from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from core.models import CustomUser
from core.permissions import ALL, BusinessRulesMixin, RoleScopedQuerySet
from patient.models import Patient
from utils.fields import EncryptedTextField

Role = CustomUser.Role


class AppointmentRequestQuerySet(RoleScopedQuerySet):
    VISIBLE_TO = {
        Role.SUPERVISOR: ALL,
        Role.ADMINISTRATIVO: ALL,
        Role.PACIENTE: lambda u: Q(patient_id=u.pk),
    }


class AppointmentRequest(BusinessRulesMixin, models.Model):
    class Period(models.TextChoices):
        MORNING = "MO", "Manhã"
        AFTERNOON = "AF", "Tarde"
        EVENING = "EV", "Noite"

    class Status(models.TextChoices):
        PENDING = "PE", "Pendente"
        ACCEPTED = "AC", "Aceita"
        DECLINED = "DE", "Recusada"

    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="appointment_requests",
        verbose_name="Paciente",
    )

    preferred_date = models.DateField(verbose_name="Data preferida")

    preferred_period = models.CharField(
        max_length=2,
        choices=Period.choices,
        verbose_name="Período preferido",
    )

    notes = EncryptedTextField(blank=True, verbose_name="Observações")

    status = models.CharField(
        max_length=2,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Situação",
    )

    response = models.TextField(blank=True, verbose_name="Resposta")

    answered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="answered_appointment_requests",
        verbose_name="Respondida por",
    )

    answered_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Respondida em",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Solicitada em")

    objects = AppointmentRequestQuerySet.as_manager()

    CREATABLE_BY = (Role.PACIENTE,)
    EDITABLE_FIELDS = {
        Role.ADMINISTRATIVO: ("status", "response", "answered_by", "answered_at"),
    }
    DELETABLE_BY = ()

    class Meta:
        verbose_name = "Solicitação de horário"
        verbose_name_plural = "Solicitações de horário"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["patient"],
                condition=Q(status="PE"),
                name="one_pending_request_per_patient",
                violation_error_message=(
                    "Você já tem uma solicitação de horário pendente."
                ),
            ),
            models.CheckConstraint(
                condition=(
                    Q(status="PE", answered_at__isnull=True)
                    | (~Q(status="PE") & Q(answered_at__isnull=False))
                ),
                name="request_answered_only_when_not_pending",
            ),
        ]

    @property
    def is_pending(self):
        return self.status == self.Status.PENDING

    def clean(self):
        super().clean()
        if (
            self._state.adding
            and self.preferred_date
            and self.preferred_date < timezone.localdate()
        ):
            raise ValidationError(
                {"preferred_date": "Escolha uma data a partir de hoje."}
            )

    def answer(self, user, accepted, response=""):
        if "status" not in self.editable_fields_for(user):
            raise ValidationError(
                "Só o Administrativo responde solicitações de horário."
            )
        if not self.is_pending:
            raise ValidationError("Esta solicitação já foi respondida.")

        self.status = self.Status.ACCEPTED if accepted else self.Status.DECLINED
        self.response = response.strip()
        self.answered_by = user
        self.answered_at = timezone.now()
        self.save(update_fields=["status", "response", "answered_by", "answered_at"])

    def __str__(self):
        return f"Solicitação de {self.patient} para {self.preferred_date:%d/%m/%Y}"
