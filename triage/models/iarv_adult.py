from django.db import models

from .iarv_base import (
    BaseIarv,
    ORDINAL_VALIDATORS,
    ProtectionScale,
    RiskScale,
    RiskSeverity,
)


class IarvAdult(BaseIarv):
    triage_record = models.OneToOneField(
        "triage.TriageRecord",
        on_delete=models.CASCADE,
        related_name="iarv_adult",
        verbose_name="Ficha de triagem",
    )

    # Section 1 - Current psychiatric symptoms

    suicidal_ideation = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Ideação suicida",
    )

    self_harm = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Automutilação",
    )

    psychosis_delusions_hallucinations = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Psicose, delírios ou alucinações",
    )

    anxiety_panic = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Ansiedade e pânico",
    )

    depressed_mood = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Humor deprimido",
    )

    alcohol_drug_abuse = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Uso abusivo de álcool ou drogas",
    )

    # Section 2 - Violence and external risk

    domestic_violence = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Violência doméstica",
    )

    homelessness = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Situação de rua",
    )

    # Section 3 - Socioeconomic vulnerability

    income_and_work = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Renda e trabalho",
    )

    healthcare_access = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Acesso à rede de saúde",
    )

    housing_conditions = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Condições de moradia",
    )

    # Section 4 - Functional impairment

    daily_living_activities = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Atividades de vida diária",
    )

    work_or_studies = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Trabalho ou estudos",
    )

    family_relationships = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Relações familiares",
    )

    # Section 5 - Protection network

    family_support = models.IntegerField(
        choices=ProtectionScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Família",
    )

    community_support = models.IntegerField(
        choices=ProtectionScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Comunidade",
    )

    ongoing_treatment = models.IntegerField(
        choices=ProtectionScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Tratamento em curso",
    )

    RISK_FIELDS = (
        "suicidal_ideation",
        "self_harm",
        "psychosis_delusions_hallucinations",
        "anxiety_panic",
        "depressed_mood",
        "alcohol_drug_abuse",
        "domestic_violence",
        "homelessness",
        "income_and_work",
        "healthcare_access",
        "housing_conditions",
        "daily_living_activities",
        "work_or_studies",
        "family_relationships",
    )

    PROTECTION_FIELDS = (
        "family_support",
        "community_support",
        "ongoing_treatment",
    )

    def get_classification(self):
        score = self.calculate_score()

        if score < 0:
            return RiskSeverity.ELEVATED_PROTECTION

        if score <= 5:
            return RiskSeverity.LOW

        if score <= 11:
            return RiskSeverity.MEDIUM

        if score <= 19:
            return RiskSeverity.HIGH

        return RiskSeverity.MAXIMUM

    def __str__(self):
        return f"IarvAdult #{self.pk}"

    class Meta:
        verbose_name = "IARV Adulto"
        verbose_name_plural = "IARV Adultos"
