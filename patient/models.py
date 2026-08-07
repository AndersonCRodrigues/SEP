from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from core.models import CustomUser
from students.models import Student
from teacher.models import Teacher


class Patient(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patient_profile",
        verbose_name="Usuário",
    )

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

    active = models.BooleanField(default=True, verbose_name="Ativo")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    class Meta:
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"

    def clean(self):
        super().clean()
        if self.user_id and self.user.role != CustomUser.Role.PACIENTE:
            raise ValidationError(
                {"user": "O usuário vinculado precisa ter o cargo Paciente."}
            )

    def __str__(self):
        return self.user.nome_completo
