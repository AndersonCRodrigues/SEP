from django.db import models

from .iarv_base import (
    BaseIarv,
    ORDINAL_VALIDATORS,
    ProtectionScale,
    RiskScale,
    RiskSeverity,
)


class IarvAdolescent(BaseIarv):
    triage_record = models.OneToOneField(
        "triage.TriageRecord",
        on_delete=models.CASCADE,
        related_name="iarv_adolescent",
        verbose_name="Ficha de triagem",
    )

    # Section 1 - Current psychiatric symptoms

    suicidal_ideation = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Ideação suicida",
    )

    self_harm_behavior = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Comportamento autolesivo",
    )

    perception_thought_changes = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Alterações da percepção ou pensamento",
    )

    anxiety_panic = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Ansiedade ou pânico",
    )

    depressed_mood = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Humor deprimido",
    )

    impulsivity_aggressiveness = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Impulsividade ou agressividade",
    )

    alcohol_drug_use = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Uso de álcool ou drogas",
    )

    # Section 2 - Violence and external risk

    domestic_violence = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Violência doméstica",
    )

    physical_sexual_abuse = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Abuso físico ou sexual",
    )

    bullying_school_violence = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Bullying ou violência escolar",
    )

    community_violence_exposure = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Exposição à violência comunitária",
    )

    # Section 3 - Socioeconomic vulnerability

    family_income = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Renda familiar",
    )

    housing_conditions = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Condições de moradia",
    )

    health_school_network_access = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Acesso à rede de saúde e escola",
    )

    # Section 4 - Functional impairment

    school_functioning = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Escola",
    )

    family_relationships = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Relações familiares",
    )

    social_life = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Vida social",
    )

    # Section 5 - Protection network

    family_caregiver_support = models.IntegerField(
        choices=ProtectionScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Família ou cuidador",
    )

    school_community_support = models.IntegerField(
        choices=ProtectionScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Escola ou comunidade",
    )

    professional_follow_up = models.IntegerField(
        choices=ProtectionScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Acompanhamento profissional",
    )

    RISK_FIELDS = (
        "suicidal_ideation",
        "self_harm_behavior",
        "perception_thought_changes",
        "anxiety_panic",
        "depressed_mood",
        "impulsivity_aggressiveness",
        "alcohol_drug_use",
        "domestic_violence",
        "physical_sexual_abuse",
        "bullying_school_violence",
        "community_violence_exposure",
        "family_income",
        "housing_conditions",
        "health_school_network_access",
        "school_functioning",
        "family_relationships",
        "social_life",
    )

    PROTECTION_FIELDS = (
        "family_caregiver_support",
        "school_community_support",
        "professional_follow_up",
    )

    def get_classification(self):
        score = self.calculate_score()

        if score < 0:
            return RiskSeverity.ELEVATED_PROTECTION

        if score <= 4:
            return RiskSeverity.LOW

        if score <= 9:
            return RiskSeverity.MEDIUM

        if score <= 17:
            return RiskSeverity.HIGH

        return RiskSeverity.MAXIMUM

    def __str__(self):
        return f"IarvAdolescent #{self.pk}"

    class Meta:
        verbose_name = "IARV Adolescente"
        verbose_name_plural = "IARV Adolescentes"