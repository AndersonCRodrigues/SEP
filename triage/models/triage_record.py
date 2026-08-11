from django.db import models

from patient.models import Patient
from students.models import Aluno
from utils.fields import EncryptedTextField


class TriageRecord(models.Model):
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
        Aluno,
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

        if (
            is_new
            and self.patient.flow_status != Patient.FlowStatus.IN_TRIAGE
        ):
            self.patient.flow_status = Patient.FlowStatus.IN_TRIAGE
            self.patient.save(update_fields=["flow_status"])

    def __str__(self):
        return f"TriageRecord #{self.pk}"