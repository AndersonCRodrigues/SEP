from django.conf import settings
from django.db import models
from django.db.models import F, Q
from areas.models import AreaActing
from core.models import CustomUser
from core.permissions import ALL, BusinessRulesMixin, RoleScopedQuerySet
from patient.models import Patient, with_open_case
from scheduling.models import Appointment
from students.models import Student

Role = CustomUser.Role


class BaseCertificate(BusinessRulesMixin, models.Model):
    content = models.TextField(verbose_name="Conteúdo")

    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="%(class)s_set",
        verbose_name="Emitido por",
    )

    issued_at = models.DateField(verbose_name="Data de emissão")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    DOCUMENT_FIELDS = ("content", "issued_at")

    CREATABLE_BY = (Role.ADMINISTRATIVO,)
    DELETABLE_BY = ()

    class Meta:
        abstract = True
        ordering = ["-issued_at"]


class AttendanceCertificateQuerySet(RoleScopedQuerySet):
    VISIBLE_TO = {
        Role.SUPERVISOR: ALL,
        Role.ADMINISTRATIVO: ALL,
        Role.PROFESSOR: lambda u: (
            with_open_case("patient__", student__current_advisor_id=u.pk)
            | Q(patient__responsible_teachers=u.pk)
        ),
        Role.ALUNO: lambda u: with_open_case("patient__", student_id=u.pk),
        Role.PACIENTE: lambda u: Q(patient_id=u.pk),
    }


class AttendanceCertificate(BaseCertificate):
    """Comprova ao paciente a ida ao atendimento."""

    class Kind(models.TextChoices):
        DECLARATION = "DE", "Declaração de comparecimento"
        MEDICAL_CERTIFICATE = "AT", "Atestado"

    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="certificates",
        verbose_name="Paciente",
    )

    appointment = models.ForeignKey(
        Appointment,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="certificates",
        verbose_name="Atendimento",
    )

    acting_area = models.ForeignKey(
        AreaActing,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="certificates",
        verbose_name="Área de atuação",
    )

    kind = models.CharField(
        max_length=2,
        choices=Kind.choices,
        default=Kind.DECLARATION,
        verbose_name="Tipo",
    )

    objects = AttendanceCertificateQuerySet.as_manager()

    EDITABLE_FIELDS = {
        role: BaseCertificate.DOCUMENT_FIELDS + ("kind", "appointment")
        for role in (Role.PROFESSOR, Role.ADMINISTRATIVO)
    }

    class Meta(BaseCertificate.Meta):
        verbose_name = "Declaração de comparecimento"
        verbose_name_plural = "Declarações de comparecimento"

    def __str__(self):
        return f"{self.get_kind_display()} de {self.patient} ({self.issued_at})"


class InternshipDeclarationQuerySet(RoleScopedQuerySet):
    VISIBLE_TO = {
        Role.SUPERVISOR: ALL,
        Role.ADMINISTRATIVO: ALL,
        Role.PROFESSOR: lambda u: Q(student__current_advisor_id=u.pk),
        Role.ALUNO: lambda u: Q(student_id=u.pk),
    }


class InternshipDeclaration(BaseCertificate):
    """Comprova à universidade as horas de estágio cumpridas no período."""

    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="declarations",
        verbose_name="Aluno",
    )

    start_date = models.DateField(verbose_name="Início do período")

    end_date = models.DateField(verbose_name="Fim do período")

    total_minutes = models.PositiveIntegerField(verbose_name="Total em minutos")

    objects = InternshipDeclarationQuerySet.as_manager()

    EDITABLE_FIELDS = {
        role: BaseCertificate.DOCUMENT_FIELDS
        + ("start_date", "end_date", "total_minutes")
        for role in (Role.PROFESSOR, Role.ADMINISTRATIVO)
    }

    class Meta(BaseCertificate.Meta):
        verbose_name = "Declaração de estágio"
        verbose_name_plural = "Declarações de estágio"
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=F("start_date")),
                name="internship_period_is_ordered",
            )
        ]

    @property
    def total_hours(self):
        return round(self.total_minutes / 60, 2)

    def __str__(self):
        return f"Declaração de estágio de {self.student} ({self.total_hours}h)"
