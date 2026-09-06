"""Orientação: o único par ponteiro/histórico que sobrou no projeto."""

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.db.models import Q, UniqueConstraint
from django.utils import timezone
from core.models import CustomUser
from core.permissions import BusinessRulesMixin, RoleScopedQuerySet
from teacher.models import Teacher
from .scoping import current_term
from .student import Student

Role = CustomUser.Role


class AdvisingQuerySet(RoleScopedQuerySet):
    def visible_to(self, user):
        if not user.is_authenticated:
            return self.none()

        role = user.role
        if role == Role.SUPERVISOR:
            return self
        if role == Role.PROFESSOR:
            return self.filter(teacher_id=user.pk)
        if role == Role.ALUNO:
            return self.filter(student_id=user.pk)
        return self.none()


class AdvisingManager(models.Manager.from_queryset(AdvisingQuerySet)):
    @transaction.atomic
    def sync_from_student(self, student, term=None):
        open_row = (
            self.select_for_update()
            .filter(student=student, end_date__isnull=True)
            .first()
        )
        if open_row:
            open_row.end_date = timezone.now().date()
            open_row._from_sync = True
            open_row.save(update_fields=["end_date"])

        if student.current_advisor_id is None:
            return None

        row = self.model(
            student=student,
            teacher_id=student.current_advisor_id,
            term=term or current_term(),
        )
        row._from_sync = True
        row.save()
        return row

    @transaction.atomic
    def change_advisor(self, student, new_teacher, term=None):
        if student.current_advisor_id == getattr(new_teacher, "pk", None):
            raise ValidationError("O aluno ja esta sendo orientado por este professor.")

        student._advising_term = term
        student.current_advisor = new_teacher
        student.save(update_fields=["current_advisor"])

        return self.filter(student=student, end_date__isnull=True).first()


class Advising(BusinessRulesMixin, models.Model):
    student = models.ForeignKey(
        Student,
        related_name="advising_history",
        on_delete=models.PROTECT,
        verbose_name="Aluno",
    )
    teacher = models.ForeignKey(
        Teacher,
        related_name="advisee_history",
        on_delete=models.PROTECT,
        verbose_name="Professor",
    )

    term = models.CharField(
        max_length=6,
        validators=[
            RegexValidator(
                regex=r"^\d{4}\.[12]$",
                message="O  período deve estar no formato AAAA.1 ou AAAA.2 (exemplo.:2026.1).",
            )
        ],
        verbose_name="Período",
    )  # ex: "2026.1"

    start_date = models.DateField(auto_now_add=True, verbose_name="Data de início")
    end_date = models.DateField(null=True, blank=True, verbose_name="Data de término")

    objects = AdvisingManager()

    CREATABLE_BY = (Role.PROFESSOR,)
    EDITABLE_FIELDS = {
        Role.SUPERVISOR: ("teacher", "term", "end_date"),
        Role.PROFESSOR: ("end_date",),
    }
    DELETABLE_BY = ()

    @classmethod
    def can_be_created_by(cls, user, teacher=None, **context):
        if not super().can_be_created_by(user):
            return False
        if user.role == Role.PROFESSOR:
            return teacher is not None and teacher.pk == user.pk
        return True

    class Meta:
        verbose_name = "Orientação"
        verbose_name_plural = "Orientações"
        constraints = [
            UniqueConstraint(
                fields=["student"],
                condition=Q(end_date__isnull=True),
                name="student_with_at_most_one_active_advising",
            )
        ]

    def save(self, *args, **kwargs):
        if not getattr(self, "_from_sync", False):
            raise ValueError(
                "Histórico é derivado: mova Student.current_advisor "
                "(Advising.objects.change_advisor)."
            )
        super().save(*args, **kwargs)

    def __str__(self):
        status = "ativa" if self.end_date is None else f"encerrada em {self.end_date}"
        return f"{self.student} orientado por {self.teacher} ({self.term}, {status})"
