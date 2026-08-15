from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.db.models import Q, Sum, UniqueConstraint
from django.utils import timezone
from areas.models import AreaActing
from core.models import CustomUser
from core.permissions import BusinessRulesMixin, RoleScopedQuerySet
from teacher.models import Teacher
from decimal import Decimal

Role = CustomUser.Role


def current_term(today=None):
    today = today or timezone.now().date()
    return f"{today.year}.{1 if today.month <= 6 else 2}"


class Student(CustomUser):
    current_advisor = models.ForeignKey(
        Teacher,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="current_advisees",
        verbose_name="Orientador atual",
    )

    current_patient = models.ForeignKey(
        "patient.Patient",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="responsible_students",
        verbose_name="Paciente atual",
    )

    MAX_STUDENTS_PER_PATIENT = 2

    class Meta:
        verbose_name = "Aluno"
        verbose_name_plural = "Alunos"

    @property
    def acting_area(self):
        return self.current_advisor.acting_area if self.current_advisor_id else None

    @classmethod
    def has_room_for(cls, patient, ignoring=None):
        ocupantes = cls.objects.filter(current_patient=patient)
        if ignoring is not None and ignoring.pk:
            ocupantes = ocupantes.exclude(pk=ignoring.pk)
        return ocupantes.count() < cls.MAX_STUDENTS_PER_PATIENT

    def clean(self):
        super().clean()
        if self.current_patient_id is None:
            return

        if not Student.has_room_for(self.current_patient_id, ignoring=self):
            raise ValidationError(
                {
                    "current_patient": (
                        f"Este paciente já tem {self.MAX_STUDENTS_PER_PATIENT} "
                        "alunos responsáveis."
                    )
                }
            )

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

    CREATABLE_BY = (Role.SUPERVISOR, Role.PROFESSOR)
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


class CaseAssignmentManager(models.Manager.from_queryset(AdviseeScopedQuerySet)):
    @transaction.atomic
    def sync_from_student(self, student):
        open_row = (
            self.select_for_update()
            .filter(student=student, end_date__isnull=True)
            .first()
        )
        if open_row:
            open_row.end_date = timezone.now().date()
            open_row._from_sync = True
            open_row.save(update_fields=["end_date"])

        if student.current_patient_id is None:
            return None

        row = self.model(
            student=student,
            patient_id=student.current_patient_id,
            acting_area=student.acting_area,
        )
        row._from_sync = True
        row.save()
        return row

    @transaction.atomic
    def change_patient(self, student, new_patient):
        if student.current_patient_id == getattr(new_patient, "pk", None):
            raise ValidationError("O aluno ja esta encarregado deste paciente.")

        if new_patient is not None and not Student.has_room_for(
            new_patient, ignoring=student
        ):
            raise ValidationError(
                f"Este paciente ja tem {Student.MAX_STUDENTS_PER_PATIENT} "
                "alunos responsaveis."
            )

        student.current_patient = new_patient
        student.save(update_fields=["current_patient"])

        return self.filter(student=student, end_date__isnull=True).first()


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

    CREATABLE_BY = (Role.SUPERVISOR, Role.PROFESSOR)
    EDITABLE_FIELDS = {
        Role.SUPERVISOR: ("end_date",),
        Role.PROFESSOR: ("end_date",),
    }
    DELETABLE_BY = ()

    class Meta:
        verbose_name = "Designação de caso"
        verbose_name_plural = "Designações de caso"
        ordering = ["-start_date"]
        constraints = [
            UniqueConstraint(
                fields=["student"],
                condition=Q(end_date__isnull=True),
                name="student_with_at_most_one_active_case",
            )
        ]

    @classmethod
    def can_be_created_by(cls, user, student=None, **context):
        if not super().can_be_created_by(user):
            return False
        if user.role == Role.PROFESSOR:
            return student is not None and student.current_advisor_id == user.pk
        return True

    def save(self, *args, **kwargs):
        if not getattr(self, "_from_sync", False):
            raise ValueError(
                "Histórico é derivado: mova Student.current_patient "
                "(CaseAssignment.objects.change_patient)."
            )
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
        return student is not None and student.current_advisor_id == user.pk

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
        return student is not None and student.current_advisor_id == user.pk

    def __str__(self):
        return f"Avaliação de {self.student} por {self.teacher}"


class StudentActivity(BusinessRulesMixin, models.Model):
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

    CREATABLE_BY = (Role.PROFESSOR, Role.SUPERVISOR)
    EDITABLE_FIELDS = {
        Role.PROFESSOR: ("date", "activity_type", "hours_worked", "notes"),
        Role.SUPERVISOR: ("date", "activity_type", "hours_worked", "notes"),
    }
    DELETABLE_BY = (Role.PROFESSOR, Role.SUPERVISOR)

    class Meta:
        verbose_name = "Atividade de estágio"
        verbose_name_plural = "Atividades de estágio"
        ordering = ["-date"]
        constraints = [
            UniqueConstraint(
                fields=["appointment"],
                condition=Q(appointment__isnull=False),
                name="one_activity_per_appointment",
            )
        ]

    @classmethod
    def can_be_created_by(cls, user, student=None, **context):
        if not super().can_be_created_by(user):
            return False
        if student is None:
            return False
        if user.role == Role.SUPERVISOR:
            return True
        if user.role == Role.PROFESSOR:
            return student.current_advisor_id == user.pk
        return False

    def editable_fields_for(self, user):
        if self.appointment_id:
            return ()
        return super().editable_fields_for(user)

    def can_be_deleted_by(self, user):
        if self.appointment_id:
            return False
        return super().can_be_deleted_by(user)

    @classmethod
    def total_hours_for(cls, student, start_date, end_date):
        total = cls.objects.filter(
            student=student, date__gte=start_date, date__lte=end_date
        ).aggregate(total=Sum("hours_worked"))["total"]
        return total or Decimal("0")

    def __str__(self):
        return f"{self.get_activity_type_display()} de {self.student} em {self.date} ({self.hours_worked}h)"