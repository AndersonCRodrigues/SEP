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
    def open_cases(self):
        return self.case_history.filter(end_date__isnull=True)

    @property
    def acting_area(self):
        """A area em que o aluno atua vem do caso aberto, nao do orientador."""
        caso = self.open_cases.first()
        return caso.acting_area if caso else None

    @property
    def default_acting_area(self):
        """So resolve sozinho quando o orientador atua numa area unica."""
        if not self.current_advisor_id:
            return None
        areas = list(self.current_advisor.acting_areas.all()[:2])
        return areas[0] if len(areas) == 1 else None

    def enforce_role(self):
        self.role = CustomUser.Role.ALUNO

    def __str__(self):
        return self.nome_completo
