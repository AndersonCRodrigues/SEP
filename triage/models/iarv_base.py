from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from core.models import CustomUser
from core.permissions import ALL, BusinessRulesMixin, RoleScopedQuerySet
from triage.constants import VISIBLE_TO_AUTHOR

Role = CustomUser.Role


class IarvQuerySet(RoleScopedQuerySet):
    VISIBLE_TO = {
        Role.SUPERVISOR: ALL,
        Role.PROFESSOR: lambda u: Q(
            triage_record__student_author__current_advisor_id=u.pk
        ),
        Role.ALUNO: lambda u: Q(
            triage_record__student_author_id=u.pk,
            triage_record__status__in=VISIBLE_TO_AUTHOR,
        ),
    }


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


class BaseIarv(BusinessRulesMixin, models.Model):
    RISK_FIELDS = ()
    PROTECTION_FIELDS = ()

    objects = IarvQuerySet.as_manager()

    CONTROL_FIELDS = frozenset({"id", "triage_record"})

    CREATABLE_BY = (Role.ALUNO,)
    DELETABLE_BY = ()

    @classmethod
    def editable_fields_for_role(cls, role):
        if role not in (Role.ALUNO, Role.SUPERVISOR):
            return ()
        return tuple(
            f.name
            for f in cls._meta.concrete_fields
            if f.name not in cls.CONTROL_FIELDS
        )

    def editable_fields_for(self, user):
        if (
            user.is_authenticated
            and user.role == Role.ALUNO
            and not self.triage_record.is_open
        ):
            return ()
        return super().editable_fields_for(user)

    class Meta:
        abstract = True

    def calculate_risk_sum(self):
        return sum(getattr(self, field_name) for field_name in self.RISK_FIELDS)

    def calculate_protection_sum(self):
        return sum(getattr(self, field_name) for field_name in self.PROTECTION_FIELDS)

    def calculate_score(self):
        return self.calculate_risk_sum() - self.calculate_protection_sum()
