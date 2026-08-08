from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from core.models import CustomUser
from core.permissions import BusinessRulesMixin, RoleScopedQuerySet
from patient.models import Patient
from students.models import Student

Role = CustomUser.Role


class CertificateQuerySet(RoleScopedQuerySet):
    def visible_to(self, user):
        if not user.is_authenticated:
            return self.none()

        role = user.role
        if role in (Role.SUPERVISOR, Role.PROFESSOR, Role.ADMIN):
            return self
        if role == Role.ALUNO:
            return self.filter(
                Q(student_id=user.pk) | Q(patient__responsible_student_id=user.pk)
            ).distinct()
        if role == Role.PACIENTE:
            return self.filter(patient_id=user.pk)
        return self.none()


class Certificate(BusinessRulesMixin, models.Model):
    class Kind(models.TextChoices):
        DECLARATION = "DE", "Declaração"
        MEDICAL_CERTIFICATE = "AT", "Atestado"

    patient = models.ForeignKey(
        Patient,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="certificates",
        verbose_name="Paciente",
    )

    student = models.ForeignKey(
        Student,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="certificates",
        verbose_name="Aluno",
    )

    kind = models.CharField(
        max_length=2,
        choices=Kind.choices,
        default=Kind.DECLARATION,
        verbose_name="Tipo",
    )

    content = models.TextField(verbose_name="Conteúdo")

    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="issued_certificates",
        verbose_name="Emitido por",
    )

    issued_at = models.DateField(verbose_name="Data de emissão")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    objects = CertificateQuerySet.as_manager()

    DOCUMENT_FIELDS = ("kind", "content", "issued_at")

    CREATABLE_BY = (Role.ADMIN,)
    EDITABLE_FIELDS = {
        Role.SUPERVISOR: DOCUMENT_FIELDS,
        Role.PROFESSOR: DOCUMENT_FIELDS,
        Role.ADMIN: DOCUMENT_FIELDS,
    }
    DELETABLE_BY = ()

    class Meta:
        verbose_name = "Declaração/Atestado"
        verbose_name_plural = "Declarações/Atestados"
        ordering = ["-issued_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(patient__isnull=False, student__isnull=True)
                    | Q(patient__isnull=True, student__isnull=False)
                ),
                name="certificate_exactly_one_recipient",
            )
        ]

    @property
    def recipient(self):
        return self.patient or self.student

    def clean(self):
        super().clean()
        if bool(self.patient_id) == bool(self.student_id):
            raise ValidationError(
                "Informe exatamente um destinatário: paciente ou aluno."
            )

    def __str__(self):
        return f"{self.get_kind_display()} de {self.recipient} ({self.issued_at})"
