from django.db import models
from core.models import CustomUser
from students.models import Student
from teacher.models import Teacher


class Patient(CustomUser):
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

    class Meta:
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"

    def save(self, *args, **kwargs):
        self.role = CustomUser.Role.PACIENTE
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome_completo
