from django.db import models
from patient.models import Patient
from students.models import Student


class Screening(models.Model):
    class Priority(models.TextChoices):
        MAXIMUM = "MX", "Prioridade Máxima"
        HIGH = "HI", "Alta"
        MEDIUM = "ME", "Média"
        LOW = "LO", "Baixa"
        ELEVATED_PROTECTION = "EP", "Proteção elevada"

    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="screenings",
        verbose_name="Paciente",
    )

    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="conducted_screenings",
        verbose_name="Aluno responsável",
    )

    priority = models.CharField(
        max_length=2,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        verbose_name="Prioridade",
    )

    main_complaint = models.TextField(verbose_name="Queixa principal")

    notes = models.TextField(blank=True, verbose_name="Observações")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        verbose_name = "Triagem"
        verbose_name_plural = "Triagens"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Triagem de {self.patient} ({self.get_priority_display()})"
