from django.conf import settings
from django.db import models
from core.models import CustomUser
from core.permissions import BusinessRulesMixin, RoleScopedQuerySet
from patient.models import Patient
from students.models import Student
from triage.constants import TriageStatus
from utils.fields import EncryptedTextField

Role = CustomUser.Role


class TriageRecordQuerySet(RoleScopedQuerySet):
    def visible_to(self, user):
        if not user.is_authenticated:
            return self.none()

        role = user.role
        if role == Role.SUPERVISOR:
            return self
        if role == Role.PROFESSOR:
            return self.filter(student_author__current_advisor_id=user.pk)
        if role == Role.ALUNO:
            return self.filter(student_author_id=user.pk, status=TriageStatus.OPEN)
        return self.none()


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
        if user.is_authenticated and user.role == Role.ALUNO and not self.is_open:
            return ()
        return super().editable_fields_for(user)

    @property
    def is_open(self):
        return self.status == TriageStatus.OPEN

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

    def save(self, *args, **kwargs):
        is_new = self._state.adding

        super().save(*args, **kwargs)

        if is_new and self.patient.flow_status != Patient.FlowStatus.IN_TRIAGE:
            self.patient.flow_status = Patient.FlowStatus.IN_TRIAGE
            self.patient.save(update_fields=["flow_status"])

    def __str__(self):
        return f"TriageRecord #{self.pk}"


class TriageFeedbackQuerySet(RoleScopedQuerySet):
    def visible_to(self, user):
        if not user.is_authenticated:
            return self.none()

        role = user.role
        if role == Role.SUPERVISOR:
            return self
        if role == Role.PROFESSOR:
            return self.filter(triage__student_author__current_advisor_id=user.pk)
        if role == Role.ALUNO:
            return self.filter(triage__student_author_id=user.pk)
        return self.none()


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
