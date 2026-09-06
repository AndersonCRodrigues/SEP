"""O paciente e seu lugar no fluxo do serviço."""

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
from core.managers import CustomUserManager
from core.models import CustomUser
from core.permissions import BusinessRulesMixin, RoleScopedQuerySet
from students.models import with_open_case
from teacher.models import Teacher
from triage.constants import VISIBLE_TO_AUTHOR
from utils.fields import EncryptedTextField

Role = CustomUser.Role


class PatientQuerySet(RoleScopedQuerySet):
    def visible_to(self, user):
        if not user.is_authenticated:
            return self.none()

        role = user.role
        if role in (Role.SUPERVISOR, Role.ADMINISTRATIVO):
            return self
        if role == Role.PROFESSOR:
            return self.filter(
                with_open_case(student__current_advisor_id=user.pk)
                | Q(responsible_teachers=user.pk)
            ).distinct()
        if role == Role.ALUNO:
            return self.filter(
                with_open_case(student_id=user.pk)
                | Q(
                    triage_records__student_author_id=user.pk,
                    triage_records__status__in=VISIBLE_TO_AUTHOR,
                )
            ).distinct()
        if role == Role.PACIENTE:
            return self.filter(pk=user.pk)
        return self.none()


class Patient(BusinessRulesMixin, CustomUser):
    class FlowStatus(models.TextChoices):
        IN_TRIAGE = "IN_TRIAGE", "Em triagem"
        AWAITING_REVIEW = "AWAITING_REVIEW", "Aguardando parecer"
        REFERRED = "REFERRED", "Encaminhado ao professor"
        IN_TREATMENT = "IN_TREATMENT", "Em atendimento"
        DISCHARGED = "DISCHARGED", "Alta"

    flow_status = models.CharField(
        max_length=30,
        choices=FlowStatus.choices,
        blank=True,
        verbose_name="Status do fluxo",
    )

    ALLOWED_TRANSITIONS = {
        "": (FlowStatus.IN_TRIAGE, FlowStatus.IN_TREATMENT),
        FlowStatus.IN_TRIAGE: (
            FlowStatus.AWAITING_REVIEW,
            FlowStatus.REFERRED,
            FlowStatus.DISCHARGED,
        ),
        FlowStatus.AWAITING_REVIEW: (
            FlowStatus.IN_TRIAGE,
            FlowStatus.REFERRED,
            FlowStatus.DISCHARGED,
        ),
        FlowStatus.REFERRED: (
            FlowStatus.IN_TRIAGE,
            FlowStatus.IN_TREATMENT,
            FlowStatus.DISCHARGED,
        ),
        FlowStatus.IN_TREATMENT: (FlowStatus.DISCHARGED,),
        FlowStatus.DISCHARGED: (FlowStatus.IN_TRIAGE,),
    }

    medical_record = EncryptedTextField(blank=True, verbose_name="Prontuário")

    responsible_teachers = models.ManyToManyField(
        Teacher,
        blank=True,
        related_name="referred_patients",
        verbose_name="Professores responsáveis",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    objects = CustomUserManager.from_queryset(PatientQuerySet)()

    REGISTRATION_FIELDS = (
        "nome_completo",
        "cpf",
        "data_nascimento",
    ) + CustomUser.ADDRESS_FIELDS
    COMPLETION_FIELDS = ("data_nascimento",) + CustomUser.ADDRESS_FIELDS

    CREATABLE_BY = (Role.ADMINISTRATIVO,)
    EDITABLE_FIELDS = {
        Role.PROFESSOR: ("responsible_teachers",),
        Role.ADMINISTRATIVO: REGISTRATION_FIELDS,
        Role.ALUNO: COMPLETION_FIELDS,
        Role.PACIENTE: COMPLETION_FIELDS,
    }
    DELETABLE_BY = ()

    class Meta:
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"

    @property
    def current_age(self):
        if not self.data_nascimento:
            return None
        hoje = timezone.localdate()
        nascimento = self.data_nascimento
        return (
            hoje.year
            - nascimento.year
            - ((hoje.month, hoje.day) < (nascimento.month, nascimento.day))
        )

    @property
    def active_treatment(self):
        return self.flow_status == self.FlowStatus.IN_TREATMENT

    def is_treated_by(self, student):
        return self.assignment_history.filter(
            student_id=student.pk, end_date__isnull=True
        ).exists()

    def advance_to(self, new_status):
        if new_status == self.flow_status:
            return False

        if new_status not in self.ALLOWED_TRANSITIONS.get(self.flow_status, ()):
            atual = self.get_flow_status_display() or "sem fluxo"
            destino = self.FlowStatus(new_status).label
            raise ValidationError(
                {"flow_status": f"Não é possível ir de {atual} para {destino}."}
            )

        with transaction.atomic():
            self.flow_status = new_status
            self.save(update_fields=["flow_status"])

            if new_status == self.FlowStatus.DISCHARGED:
                self.assignment_history.filter(end_date__isnull=True).update(
                    end_date=timezone.localdate()
                )
        return True

    def save(self, *args, **kwargs):
        self.role = CustomUser.Role.PACIENTE
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome_completo
