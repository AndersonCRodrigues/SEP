from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
from core.managers import CustomUserManager
from core.models import CustomUser
from core.permissions import ALL, BusinessRulesMixin, RoleScopedQuerySet
from teacher.models import Teacher
from core.constants import VISIBLE_TO_AUTHOR
from utils.fields import EncryptedTextField

Role = CustomUser.Role


def with_open_case(prefix="", **lookups):
    """Q sobre Patient: caso aberto, filtrado pelo aluno ou pelo orientador dele."""
    caminho = f"{prefix}assignment_history"
    filtros = {f"{caminho}__end_date__isnull": True}
    filtros.update({f"{caminho}__{campo}": valor for campo, valor in lookups.items()})
    return Q(**filtros)


class PatientQuerySet(RoleScopedQuerySet):
    VISIBLE_TO = {
        Role.SUPERVISOR: ALL,
        Role.ADMINISTRATIVO: ALL,
        Role.PROFESSOR: lambda u: (
            with_open_case(student__current_advisor_id=u.pk)
            | Q(responsible_teachers=u.pk)
        ),
        Role.ALUNO: lambda u: (
            with_open_case(student_id=u.pk)
            | Q(
                triage_records__student_author_id=u.pk,
                triage_records__status__in=VISIBLE_TO_AUTHOR,
            )
        ),
        Role.PACIENTE: lambda u: Q(pk=u.pk),
    }


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
