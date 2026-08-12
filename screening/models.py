from django.conf import settings
from django.db import models
from core.models import CustomUser
from core.permissions import BusinessRulesMixin, RoleScopedQuerySet
from patient.models import Patient
from screening.constants import ScreeningStatus
from students.models import Student

Role = CustomUser.Role


class ScreeningQuerySet(RoleScopedQuerySet):
    def visible_to(self, user):
        if not user.is_authenticated:
            return self.none()

        role = user.role
        if role == Role.SUPERVISOR:
            return self
        if role == Role.PROFESSOR:
            return self.filter(student__current_advisor_id=user.pk)
        if role == Role.ALUNO:
            return self.filter(student_id=user.pk, status=ScreeningStatus.OPEN)
        return self.none()


class Screening(BusinessRulesMixin, models.Model):
    Status = ScreeningStatus

    class Priority(models.TextChoices):
        MAXIMUM = "MX", "Prioridade Máxima"
        HIGH = "HI", "Alta"
        MEDIUM = "ME", "Média"
        LOW = "LO", "Baixa"
        ELEVATED_PROTECTION = "EP", "Proteção elevada"

    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="screenings",
        verbose_name="Paciente",
    )

    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="conducted_screenings",
        verbose_name="Aluno responsável",
    )

    priority = models.CharField(
        max_length=2,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        verbose_name="Prioridade",
    )

    status = models.CharField(
        max_length=2,
        choices=ScreeningStatus.choices,
        default=ScreeningStatus.OPEN,
        verbose_name="Situação",
    )

    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="closed_screenings",
        verbose_name="Fechada por",
    )

    closed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fechada em",
    )

    main_complaint = models.TextField(verbose_name="Queixa principal")

    notes = models.TextField(blank=True, verbose_name="Observações")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    objects = ScreeningQuerySet.as_manager()

    FICHA_FIELDS = ("priority", "main_complaint", "notes")

    CREATABLE_BY = (Role.ALUNO,)
    EDITABLE_FIELDS = {
        Role.SUPERVISOR: FICHA_FIELDS + ("status", "closed_by", "closed_at"),
        Role.ALUNO: FICHA_FIELDS,
    }
    DELETABLE_BY = ()

    class Meta:
        verbose_name = "Triagem"
        verbose_name_plural = "Triagens"
        ordering = ["-created_at"]

    def editable_fields_for(self, user):
        if user.is_authenticated and user.role == Role.ALUNO and not self.is_open:
            return ()
        return super().editable_fields_for(user)

    @property
    def is_open(self):
        return self.status == ScreeningStatus.OPEN

    def __str__(self):
        return f"Triagem de {self.patient} ({self.get_priority_display()})"


class ScreeningFeedbackQuerySet(RoleScopedQuerySet):
    def visible_to(self, user):
        if not user.is_authenticated:
            return self.none()

        role = user.role
        if role == Role.SUPERVISOR:
            return self
        if role == Role.PROFESSOR:
            return self.filter(screening__student__current_advisor_id=user.pk)
        if role == Role.ALUNO:
            return self.filter(screening__student_id=user.pk)
        return self.none()


class ScreeningFeedback(BusinessRulesMixin, models.Model):
    screening = models.ForeignKey(
        Screening,
        on_delete=models.PROTECT,
        related_name="feedbacks",
        verbose_name="Triagem",
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="screening_feedbacks",
        verbose_name="Autor",
    )

    content = models.TextField(verbose_name="Parecer")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    objects = ScreeningFeedbackQuerySet.as_manager()

    CREATABLE_BY = (Role.SUPERVISOR, Role.PROFESSOR)
    EDITABLE_FIELDS = {
        Role.SUPERVISOR: ("content",),
        Role.PROFESSOR: ("content",),
    }
    DELETABLE_BY = ()

    class Meta:
        verbose_name = "Feedback de triagem"
        verbose_name_plural = "Feedbacks de triagem"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Feedback de {self.author.nome_completo} em {self.screening}"
