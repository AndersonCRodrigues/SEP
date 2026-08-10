from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.db.models import Q, Sum, UniqueConstraint
from django.utils import timezone
from core.models import CustomUser
from core.permissions import BusinessRulesMixin, RoleScopedQuerySet
from teacher.models import Teacher

Role = CustomUser.Role


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

    def clean(self):
        super().clean()
        if self.current_patient_id is None:
            return

        ocupantes = (
            Student.objects.filter(current_patient_id=self.current_patient_id)
            .exclude(pk=self.pk)
            .count()
        )
        if ocupantes >= self.MAX_STUDENTS_PER_PATIENT:
            raise ValidationError({
                "current_patient": (
                    f"Este paciente já tem {self.MAX_STUDENTS_PER_PATIENT} "
                    "alunos responsáveis."
                )
            })

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
    def change_advisor(self, student, new_teacher, term):

        current_advising = self.select_for_update().filter(student=student, end_date__isnull=True).first()

        if current_advising:
            if current_advising.teacher == new_teacher:
                raise ValidationError(
                    "O aluno ja esta sendo orientado por este professor."
                )
            current_advising.end_date = timezone.now().date()
            current_advising.save()

        new_advising = self.create(
        student=student,
        teacher=new_teacher,
        term=term,
        )

        student.current_advisor = new_teacher
        student.save(update_fields=["current_advisor"])

        return new_advising


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
                message="O  período deve estar no formato AAAA.1 ou AAAA.2 (exemplo.:2026.1)."
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

    class Kind(models.TextChoices):
        SESSION = "AT", "Atendimento"
        SCREENING = "TR", "Triagem"
        RECORDS = "PR", "Prontuário"
        OTHER = "OU", "Outra"

    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="activities",
        verbose_name="Aluno",
    )

    date = models.DateField(verbose_name="Data")

    kind = models.CharField(
        max_length=2,
        choices=Kind.choices,
        verbose_name="Tipo",
    )

    minutes = models.PositiveIntegerField(verbose_name="Minutos")

    appointment = models.ForeignKey(
        "patient.Appointment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="student_activities",
        verbose_name="Agendamento de origem",
    )

    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="registered_activities",
        verbose_name="Registrada por",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    objects = AdviseeScopedQuerySet.as_manager()

    CREATABLE_BY = (Role.PROFESSOR, Role.ALUNO)
    EDITABLE_FIELDS = {
        Role.PROFESSOR: ("date", "kind", "minutes"),
        Role.ALUNO: ("date", "kind", "minutes"),
    }
    DELETABLE_BY = (Role.PROFESSOR,)

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
        if user.role == Role.ALUNO:
            return student.pk == user.pk
        return student.current_advisor_id == user.pk

    def editable_fields_for(self, user):
        if self.appointment_id:
            return ()
        return super().editable_fields_for(user)

    def can_be_deleted_by(self, user):
        if self.appointment_id:
            return False
        return super().can_be_deleted_by(user)

    @classmethod
    def total_minutes_for(cls, student, start_date, end_date):
        total = cls.objects.filter(
            student=student, date__gte=start_date, date__lte=end_date
        ).aggregate(total=Sum("minutes"))["total"]
        return total or 0

    def __str__(self):
        return f"{self.get_kind_display()} de {self.student} em {self.date} ({self.minutes} min)"
