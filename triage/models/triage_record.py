from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

from core.constants import VISIBLE_TO_AUTHOR, VISIBLE_TO_PATIENT, TriageStatus
from core.models import CustomUser
from core.permissions import ALL, BusinessRulesMixin, RoleScopedQuerySet
from patient.models import Patient
from students.models import Student
from utils.fields import EncryptedTextField

Role = CustomUser.Role


class TriageRecordQuerySet(RoleScopedQuerySet):
    VISIBLE_TO = {
        Role.SUPERVISOR: ALL,
        Role.PROFESSOR: lambda u: Q(student_author__current_advisor_id=u.pk),
        Role.ALUNO: lambda u: Q(student_author_id=u.pk, status__in=VISIBLE_TO_AUTHOR),
        Role.PACIENTE: lambda u: Q(patient_id=u.pk, status__in=VISIBLE_TO_PATIENT),
    }


FLOW_BY_TRIAGE_STATUS = {
    TriageStatus.OPEN: Patient.FlowStatus.IN_TRIAGE,
    TriageStatus.SUBMITTED: Patient.FlowStatus.AWAITING_REVIEW,
    TriageStatus.CLOSED: Patient.FlowStatus.AWAITING_REVIEW,
    TriageStatus.REFERRED: Patient.FlowStatus.REFERRED,
    TriageStatus.FINALIZED_EDITION: Patient.FlowStatus.AWAITING_REVIEW,
}


class TriageRecord(BusinessRulesMixin, models.Model):
    class ArrivalMethod(models.TextChoices):
        SPONTANEOUS = "SPONTANEOUS", "Demanda espontânea"
        REFERRED = "REFERRED", "Encaminhado ou indicado"

    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="triage_records",
        verbose_name="Paciente",
    )

    student_author = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="authored_triage_records",
        verbose_name="Aluno autor",
    )

    arrival_method = models.CharField(
        max_length=20,
        choices=ArrivalMethod.choices,
        blank=True,
        verbose_name="Como chegou ao Serviço Escola de Psicologia",
    )

    referral_source = EncryptedTextField(
        blank=True,
        verbose_name="Encaminhado ou indicado por",
    )

    has_family_member_in_service = models.BooleanField(
        default=False,
        verbose_name="Possui familiar em atendimento no SEP",
    )

    family_member_name = EncryptedTextField(
        blank=True,
        verbose_name="Nome do familiar em atendimento",
    )

    family_relationship = EncryptedTextField(
        blank=True,
        verbose_name="Parentesco com o familiar",
    )

    is_university_student = models.BooleanField(
        default=False,
        verbose_name="É aluno da Universidade de Vassouras",
    )

    course_and_period = EncryptedTextField(
        blank=True,
        verbose_name="Curso e período",
    )

    has_close_relationship_with_student = models.BooleanField(
        default=False,
        verbose_name="Possui relação próxima com aluno que atua no SEP",
    )

    related_student_details = EncryptedTextField(
        blank=True,
        verbose_name="Aluno com quem possui relação próxima",
    )

    chief_complaint = EncryptedTextField(
        verbose_name="Queixa principal",
    )

    complaint_history = EncryptedTextField(
        blank=True,
        verbose_name="Evolução da queixa",
    )

    history = EncryptedTextField(
        blank=True,
        verbose_name="Histórico",
    )

    mental_health_treatment_history = EncryptedTextField(
        blank=True,
        verbose_name="Histórico de tratamento em saúde mental",
    )

    medical_treatment_history = EncryptedTextField(
        blank=True,
        verbose_name="Histórico de tratamento médico",
    )

    has_primary_care_connection = models.BooleanField(
        default=False,
        verbose_name="Possui vínculo com a rede de atenção básica",
    )

    primary_care_details = EncryptedTextField(
        blank=True,
        verbose_name="Detalhes do vínculo com a atenção básica",
    )

    uses_public_service = models.BooleanField(
        default=False,
        verbose_name="Frequenta equipamento público do município",
    )

    public_service_details = EncryptedTextField(
        blank=True,
        verbose_name="Equipamento público frequentado",
    )

    family_history = EncryptedTextField(
        blank=True,
        verbose_name="Breve histórico familiar",
    )

    social_support_network = EncryptedTextField(
        blank=True,
        verbose_name="Rede de suporte social",
    )

    treatment_expectations = EncryptedTextField(
        blank=True,
        verbose_name="Expectativa em relação ao atendimento psicológico",
    )

    additional_information = EncryptedTextField(
        blank=True,
        verbose_name="Outras informações relevantes",
    )

    availability = EncryptedTextField(
        blank=True,
        verbose_name="Dias e horários disponíveis para atendimento",
    )

    accepts_waiting_room_group = models.BooleanField(
        default=False,
        verbose_name="Aceita participar de grupo de sala de espera",
    )

    summary_and_impressions = EncryptedTextField(
        blank=True,
        verbose_name="Resumo e impressões",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data da triagem",
    )
    updated_at = models.DateTimeField(auto_now=True)

    status = models.CharField(
        max_length=2,
        choices=TriageStatus.choices,
        default=TriageStatus.OPEN,
        verbose_name="Situação",
    )

    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="closed_triage_records",
        verbose_name="Fechada por",
    )

    closed_at = models.DateTimeField(null=True, blank=True, verbose_name="Fechada em")
    submitted_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Enviado em"
    )

    objects = TriageRecordQuerySet.as_manager()

    CONTROL_FIELDS = frozenset(
        {
            "id",
            "patient",
            "student_author",
            "status",
            "closed_by",
            "closed_at",
            "created_at",
        }
    )

    CREATABLE_BY = (Role.ALUNO,)
    DELETABLE_BY = ()

    class Meta:
        verbose_name = "Triagem"
        verbose_name_plural = "Triagens"
        ordering = ["-created_at"]

    @classmethod
    def ficha_fields(cls):
        return tuple(
            f.name
            for f in cls._meta.concrete_fields
            if f.name not in cls.CONTROL_FIELDS
        )

    @classmethod
    def editable_fields_for_role(cls, role):
        if role == Role.ALUNO:
            return cls.ficha_fields()
        if role == Role.SUPERVISOR:
            return cls.ficha_fields() + ("status", "closed_by", "closed_at")
        return ()

    def editable_fields_for(self, user):
        if (
            user.is_authenticated
            and user.role == Role.ALUNO
            and self.status not in (TriageStatus.OPEN, TriageStatus.SUBMITTED)
        ):
            return ()
        return super().editable_fields_for(user)

    @property
    def is_open(self):
        return self.status == TriageStatus.OPEN

    @property
    def is_finalized_edition(self):
        return self.status == TriageStatus.FINALIZED_EDITION

    def get_iarv(self):
        relations = (
            "iarv_adult",
            "iarv_adolescent",
            "iarv_child",
        )

        for relation in relations:
            if hasattr(self, relation):
                return getattr(self, relation)

        return None

    def calculate_total_risk(self):
        iarv = self.get_iarv()

        if iarv is None:
            return None

        return iarv.calculate_score()

    def get_risk_classification(self):
        iarv = self.get_iarv()

        if iarv is None:
            return None

        return iarv.get_classification()

    def submit(self, student):
        if self.status != TriageStatus.OPEN:
            raise ValidationError("Só uma triagem aberta pode ser enviada.")
        if student.pk != self.student_author_id:
            raise ValidationError("Só o autor envia a própria triagem.")

        self.status = TriageStatus.SUBMITTED
        self.submitted_at = timezone.now()
        self.save(update_fields=["status", "submitted_at"])

    def finalize_edition(self, user):
        if self.status != TriageStatus.SUBMITTED:
            raise ValidationError(
                "Apenas triagens enviadas podem ter sua edição finalizada."
            )
        if user.role != Role.SUPERVISOR:
            raise ValidationError("Apenas supervisores podem fechar a edição.")

        self.status = TriageStatus.FINALIZED_EDITION
        self.save(update_fields=["status", "updated_at"])

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        anterior = (
            None
            if is_new
            else TriageRecord.objects.filter(pk=self.pk)
            .values_list("status", flat=True)
            .first()
        )

        with transaction.atomic():
            super().save(*args, **kwargs)

            # 1. Se a triagem acabou de ser criada (OPEN), move o paciente para IN_TRIAGE ("Em triagem")
            if is_new:
                paciente = Patient.objects.select_for_update().get(pk=self.patient_id)
                if paciente.flow_status != Patient.FlowStatus.IN_TRIAGE:
                    paciente.advance_to(Patient.FlowStatus.IN_TRIAGE)

            # 2. Se o status mudou (ex: OPEN -> SUBMITTED), avança para AWAITING_REVIEW ("Aguardando parecer")
            elif anterior is not None and self.status != anterior:
                novo_fluxo = FLOW_BY_TRIAGE_STATUS.get(self.status)
                if novo_fluxo:
                    paciente = Patient.objects.select_for_update().get(
                        pk=self.patient_id
                    )
                    paciente.advance_to(novo_fluxo)


class TriageFeedbackQuerySet(RoleScopedQuerySet):
    VISIBLE_TO = {
        Role.SUPERVISOR: ALL,
        Role.PROFESSOR: lambda u: Q(triage__student_author__current_advisor_id=u.pk),
        Role.ALUNO: lambda u: Q(triage__student_author_id=u.pk),
    }


class TriageFeedback(BusinessRulesMixin, models.Model):
    triage = models.ForeignKey(
        TriageRecord,
        on_delete=models.PROTECT,
        related_name="feedbacks",
        verbose_name="Triagem",
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="triage_feedbacks",
        verbose_name="Autor",
    )

    content = models.TextField(verbose_name="Parecer")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    objects = TriageFeedbackQuerySet.as_manager()

    CREATABLE_BY = (Role.PROFESSOR,)
    EDITABLE_FIELDS = {Role.PROFESSOR: ("content",)}
    DELETABLE_BY = ()

    class Meta:
        verbose_name = "Feedback de triagem"
        verbose_name_plural = "Feedbacks de triagem"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Feedback de {self.author.nome_completo} em {self.triage}"
