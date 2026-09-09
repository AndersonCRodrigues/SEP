from django.conf import settings
from django.db import models
from django.db.models import UniqueConstraint
from core.models import CustomUser
from teacher.models import Teacher
from .base import AdviseeRecord

Role = CustomUser.Role


class Attendance(AdviseeRecord):
    date = models.DateField(verbose_name="Data")

    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="registered_attendances",
        verbose_name="Registrada por",
    )

    notes = models.TextField(blank=True, verbose_name="Observações")

    EDITABLE_FIELDS = {Role.PROFESSOR: ("date", "notes")}

    class Meta(AdviseeRecord.Meta):
        verbose_name = "Presença"
        verbose_name_plural = "Presenças"
        ordering = ["-date"]
        constraints = [
            UniqueConstraint(
                fields=["student", "date"],
                name="one_attendance_per_student_per_day",
            )
        ]

    def __str__(self):
        return f"{self.student} presente em {self.date}"


class PerformanceReview(AdviseeRecord):
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.PROTECT,
        related_name="performance_reviews",
        verbose_name="Professor",
    )

    content = models.TextField(verbose_name="Avaliação")

    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    EDITABLE_FIELDS = {Role.PROFESSOR: ("content",)}

    class Meta(AdviseeRecord.Meta):
        verbose_name = "Avaliação de desempenho"
        verbose_name_plural = "Avaliações de desempenho"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Avaliação de {self.student} por {self.teacher}"
