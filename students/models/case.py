from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q, UniqueConstraint
from django.utils import timezone
from areas.models import AreaActing
from core.models import CustomUser
from core.permissions import BusinessRulesMixin
from .scoping import AdviseeScopedQuerySet, can_reach_student
from .student import Student

Role = CustomUser.Role


class CaseAssignmentQuerySet(AdviseeScopedQuerySet):
    def open(self):
        return self.filter(end_date__isnull=True)


class CaseAssignmentManager(models.Manager.from_queryset(CaseAssignmentQuerySet)):
    @transaction.atomic
    def assign(self, student, patient, acting_area=None):
        caso = self.model(
            student=student,
            patient=patient,
            acting_area=acting_area or student.acting_area,
        )
        caso.save()
        patient.advance_to(patient.FlowStatus.IN_TREATMENT)
        return caso

    @transaction.atomic
    def release(self, case):
        if case.end_date is not None:
            raise ValidationError("Este caso já está encerrado.")

        case.end_date = timezone.now().date()
        case.save(update_fields=["end_date"])
        return case


class CaseAssignment(BusinessRulesMixin, models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="case_history",
        verbose_name="Aluno",
    )

    patient = models.ForeignKey(
        "patient.Patient",
        on_delete=models.PROTECT,
        related_name="assignment_history",
        verbose_name="Paciente",
    )

    acting_area = models.ForeignKey(
        AreaActing,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="case_assignments",
        verbose_name="Área de atuação",
    )

    start_date = models.DateField(auto_now_add=True, verbose_name="Data de início")
    end_date = models.DateField(null=True, blank=True, verbose_name="Data de término")

    objects = CaseAssignmentManager()

    MAX_STUDENTS_PER_PATIENT = 2

    CREATABLE_BY = (Role.PROFESSOR,)
    EDITABLE_FIELDS = {Role.PROFESSOR: ("end_date",)}
    DELETABLE_BY = ()

    class Meta:
        verbose_name = "Designação de caso"
        verbose_name_plural = "Designações de caso"
        ordering = ["-start_date"]
        constraints = [
            UniqueConstraint(
                fields=["student", "patient"],
                condition=Q(end_date__isnull=True),
                name="one_open_case_per_student_and_patient",
            )
        ]

    @classmethod
    def can_be_created_by(cls, user, student=None, **context):
        if not super().can_be_created_by(user):
            return False
        return can_reach_student(user, student)

    def clean(self):
        super().clean()
        if self.end_date is not None:
            return

        abertos = CaseAssignment.objects.open().filter(patient_id=self.patient_id)
        if self.pk:
            abertos = abertos.exclude(pk=self.pk)

        if abertos.filter(student_id=self.student_id).exists():
            raise ValidationError({"student": "Este aluno já atende este paciente."})

        if abertos.count() >= self.MAX_STUDENTS_PER_PATIENT:
            raise ValidationError(
                {
                    "patient": (
                        f"Este paciente já tem {self.MAX_STUDENTS_PER_PATIENT} "
                        "alunos responsáveis."
                    )
                }
            )

    def save(self, *args, **kwargs):
        if self._state.adding and self.end_date is None:
            self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        status = "ativa" if self.end_date is None else f"encerrada em {self.end_date}"
        return f"{self.student} encarregado de {self.patient} ({status})"
