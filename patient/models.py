from django.db import models
from django.utils import timezone
from utils.fields import EncryptedTextField
from core.models import CustomUser

class Patient(CustomUser):
    class FlowStatus(models.TextChoices):
        IN_TRIAGE = "IN_TRIAGE", "Em triagem"

    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data de nascimento",
    )

    flow_status = models.CharField(
        max_length=30,
        choices=FlowStatus.choices,
        blank=True,
                        verbose_name="Status do fluxo",
    )

    medical_record = EncryptedTextField(
        blank=True,
        verbose_name="Prontuário",
    )

    @property
    def current_age(self):
        if not self.birth_date:
            return None

        today = timezone.localdate()

        return (
            today.year
            - self.birth_date.year
            - (
                (today.month, today.day)
                < (self.birth_date.month, self.birth_date.day)
            )
        )

    def save(self, *args, **kwargs):
        self.role = CustomUser.Role.PACIENTE
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome_completo
