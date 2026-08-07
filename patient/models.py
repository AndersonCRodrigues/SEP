from django.conf import settings
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


class ProgressNote(models.Model):
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

    class Meta:
        verbose_name = "Evolução"
        verbose_name_plural = "Evoluções"
        ordering = ["-session_date"]

    @property
    def pending_confirmation(self):
        return self.confirmed_at is None

    def __str__(self):
        return f"Evolução de {self.patient} em {self.session_date}"


class Appointment(models.Model):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="appointments",
        verbose_name="Paciente",
    )

    assigned_student = models.ForeignKey(
        Student,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="appointments",
        verbose_name="Aluno que atende",
    )

    scheduled_at = models.DateTimeField(verbose_name="Data e hora")

    notes = models.TextField(blank=True, verbose_name="Observações")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    class Meta:
        verbose_name = "Agendamento"
        verbose_name_plural = "Agendamentos"
        ordering = ["scheduled_at"]

    def __str__(self):
        return f"{self.patient} em {self.scheduled_at:%d/%m/%Y %H:%M}"
