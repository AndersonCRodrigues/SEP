"""Carga horária: participação e realização, lançadas à mão ou por signal."""

from decimal import Decimal
from django.conf import settings
from django.db import models
from django.db.models import Q, Sum, UniqueConstraint, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from core.models import CustomUser
from core.permissions import BusinessRulesMixin
from .scoping import AdviseeScopedQuerySet, can_reach_student
from .student import Student

Role = CustomUser.Role


class StudentActivity(BusinessRulesMixin, models.Model):
    PARTICIPATION_HOURS = Decimal("1.00")

    class Category(models.TextChoices):
        PARTICIPATION = "PA", "Participação"
        EXECUTION = "EX", "Realização"

    class ActivityType(models.TextChoices):
        SESSION = "AT", "Atendimento"
        SCREENING = "TR", "Triagem"
        GROUP_SUPERVISION = "SG", "Supervisão em Grupo"
        RECORDS = "PR", "Prontuário"

    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="activities",
        verbose_name="Aluno",
    )

    date = models.DateField(default=timezone.now, verbose_name="Data")

    activity_type = models.CharField(
        max_length=2,
        choices=ActivityType.choices,
        verbose_name="Tipo de atividade",
    )

    category = models.CharField(
        max_length=2,
        choices=Category.choices,
        default=Category.EXECUTION,
        verbose_name="Natureza da hora",
    )

    hours_worked = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        verbose_name="Horas trabalhadas",
    )

    notes = models.TextField(blank=True, verbose_name="Observação")

    appointment = models.ForeignKey(
        "patient.Appointment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="student_activities",
        verbose_name="Agendamento de origem",
    )

    responsible_supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        limit_choices_to=Q(role__in=[Role.PROFESSOR, Role.SUPERVISOR]),
        related_name="registered_activities",
        verbose_name="Responsável pelo registro",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    objects = AdviseeScopedQuerySet.as_manager()

    CREATABLE_BY = (Role.PROFESSOR,)
    EDITABLE_FIELDS = {
        Role.PROFESSOR: ("date", "activity_type", "category", "hours_worked", "notes")
    }
    DELETABLE_BY = (Role.PROFESSOR,)

    class Meta:
        verbose_name = "Atividade de estágio"
        verbose_name_plural = "Atividades de estágio"
        ordering = ["-date"]
        constraints = [
            UniqueConstraint(
                fields=["appointment", "category"],
                condition=Q(appointment__isnull=False),
                name="one_activity_per_appointment_category",
            )
        ]

    @classmethod
    def can_be_created_by(cls, user, student=None, **context):
        if not super().can_be_created_by(user):
            return False
        return can_reach_student(user, student)

    def editable_fields_for(self, user):
        if self.appointment_id:
            return ()
        return super().editable_fields_for(user)

    def can_be_deleted_by(self, user):
        if self.appointment_id:
            return False
        return super().can_be_deleted_by(user)

    @classmethod
    def total_hours_for(cls, student, start_date, end_date, category=None):
        linhas = cls.objects.filter(
            student=student, date__gte=start_date, date__lte=end_date
        )
        if category is not None:
            linhas = linhas.filter(category=category)
        return linhas.aggregate(
            total=Coalesce(Sum("hours_worked"), Value(Decimal("0")))
        )["total"]

    def __str__(self):
        return (
            f"{self.get_activity_type_display()} ({self.get_category_display()}) "
            f"de {self.student} em {self.date} — {self.hours_worked}h"
        )
