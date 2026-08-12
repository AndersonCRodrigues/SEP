from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class RiskScale(models.IntegerChoices):
    NONE = 0, "Não / Ausente"
    MILD = 1, "Leve"
    MODERATE = 2, "Moderado"
    SEVERE = 3, "Grave"


class ProtectionScale(models.IntegerChoices):
    ABSENT = 0, "Ausente"
    WEAK = 1, "Frágil"
    PARTIAL = 2, "Parcial"
    PRESENT_STABLE = 3, "Presente e estável"


class RiskSeverity(models.TextChoices):
    ELEVATED_PROTECTION = "ELEVATED_PROTECTION", "Proteção elevada"
    LOW = "LOW", "Baixa"
    MEDIUM = "MEDIUM", "Média"
    HIGH = "HIGH", "Alta"
    MAXIMUM = "MAXIMUM", "Máxima"


ORDINAL_VALIDATORS = [
    MinValueValidator(0),
    MaxValueValidator(3),
]


class BaseIarv(models.Model):
    RISK_FIELDS = ()
    PROTECTION_FIELDS = ()

    class Meta:
        abstract = True

    def calculate_risk_sum(self):
        return sum(
            getattr(self, field_name)
            for field_name in self.RISK_FIELDS
        )

    def calculate_protection_sum(self):
        return sum(
            getattr(self, field_name)
            for field_name in self.PROTECTION_FIELDS
        )

    def calculate_score(self):
        return (
            self.calculate_risk_sum()
            - self.calculate_protection_sum()
        )