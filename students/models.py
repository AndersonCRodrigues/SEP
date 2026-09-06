from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.db.models import Q, Sum, UniqueConstraint, Value
from django.utils import timezone
from areas.models import AreaActing
from core.models import CustomUser
from core.permissions import BusinessRulesMixin, RoleScopedQuerySet
from teacher.models import Teacher
from decimal import Decimal
from django.db.models.functions import Coalesce

Role = CustomUser.Role


def current_term(today=None):
    today = today or timezone.now().date()
    return f"{today.year}.{1 if today.month <= 6 else 2}"


def with_open_case(prefix="", **lookups):
    caminho = f"{prefix}assignment_history"
    filtros = {f"{caminho}__end_date__isnull": True}
    filtros.update({f"{caminho}__{campo}": valor for campo, valor in lookups.items()})
    return Q(**filtros)


def can_reach_student(user, student):
    if student is None:
        return False
    if user.role == Role.PROFESSOR:
        return student.current_advisor_id == user.pk
    return True


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
    def acting_area(self):
        return self.current_advisor.acting_area if self.current_advisor_id else None

    @property
    def open_cases(self):
        return self.case_history.filter(end_date__isnull=True)

    def save(self, *args, **kwargs):
        self.role = CustomUser.Role.ALUNO
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome_completo


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


class AdviseeScopedQuerySet(RoleScopedQuerySet):
    def visible_to(self, user):
        if not user.is_authenticated:
            return self.none()

        role = user.role
        if role == Role.SUPERVISOR:
            return self
        if role == Role.PROFESSOR:
            return self.filter(student__current_advisor_id=user.pk)
        if role == Role.ALUNO:
            return self.filter(student_id=user.pk)
        return self.none()


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
