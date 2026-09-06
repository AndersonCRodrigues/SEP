from django.db import models
from core.models import CustomUser
from teacher.models import Teacher


class Student(CustomUser):
    class Stage(models.TextChoices):
        TRIAGE = "TR", "Triagem"
        TREATMENT = "AT", "Atendimento"

    stage = models.CharField(
        max_length=2,
        choices=Stage.choices,
        default=Stage.TRIAGE,
        verbose_name="Fase do estágio",
    )

    current_advisor = models.ForeignKey(
        Teacher,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="current_advisees",
        verbose_name="Orientador atual",
    )

    class Meta:
        verbose_name = "Aluno"
        verbose_name_plural = "Alunos"

    @property
    def in_triage(self):
        return self.stage == self.Stage.TRIAGE

    @property
    def acting_area(self):
        return self.current_advisor.acting_area if self.current_advisor_id else None

    @property
    def open_cases(self):
        return self.case_history.filter(end_date__isnull=True)

    def save(self, *args, **kwargs):
        self.role = CustomUser.Role.ALUNO
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome_completo
