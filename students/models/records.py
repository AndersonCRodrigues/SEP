"""O que o professor registra sobre o orientando: presença e avaliação."""

from django.conf import settings
from django.db import models
from django.db.models import UniqueConstraint
from core.models import CustomUser
from core.permissions import BusinessRulesMixin
from teacher.models import Teacher
from .scoping import AdviseeScopedQuerySet, can_reach_student
from .student import Student

Role = CustomUser.Role


class Attendance(BusinessRulesMixin, models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="attendances",
        verbose_name="Aluno",
    )

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

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    objects = AdviseeScopedQuerySet.as_manager()

    CREATABLE_BY = (Role.PROFESSOR,)
    EDITABLE_FIELDS = {Role.PROFESSOR: ("date", "notes")}
    DELETABLE_BY = (Role.PROFESSOR,)

    class Meta:
        verbose_name = "Presença"
        verbose_name_plural = "Presenças"
        ordering = ["-date"]
        constraints = [
            UniqueConstraint(
                fields=["student", "date"],
                name="one_attendance_per_student_per_day",
            )
        ]

    @classmethod
    def can_be_created_by(cls, user, student=None, **context):
        if not super().can_be_created_by(user):
            return False
        return can_reach_student(user, student)

    def __str__(self):
        return f"{self.student} presente em {self.date}"


class PerformanceReview(BusinessRulesMixin, models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="performance_reviews",
        verbose_name="Aluno",
    )

    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.PROTECT,
        related_name="performance_reviews",
        verbose_name="Professor",
    )

    content = models.TextField(verbose_name="Avaliação")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    objects = AdviseeScopedQuerySet.as_manager()

    CREATABLE_BY = (Role.PROFESSOR,)
    EDITABLE_FIELDS = {Role.PROFESSOR: ("content",)}
    DELETABLE_BY = (Role.PROFESSOR,)

    class Meta:
        verbose_name = "Avaliação de desempenho"
        verbose_name_plural = "Avaliações de desempenho"
        ordering = ["-updated_at"]

    @classmethod
    def can_be_created_by(cls, user, student=None, **context):
        if not super().can_be_created_by(user):
            return False
        return can_reach_student(user, student)

    def __str__(self):
        return f"Avaliação de {self.student} por {self.teacher}"
