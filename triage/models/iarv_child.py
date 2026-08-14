from django.db import models

from .iarv_base import (
    BaseIarv,
    ORDINAL_VALIDATORS,
    ProtectionScale,
    RiskScale,
    RiskSeverity,
)


class IarvChild(BaseIarv):
    triage_record = models.OneToOneField(
        "triage.TriageRecord",
        on_delete=models.CASCADE,
        related_name="iarv_child",
        verbose_name="Ficha de triagem",
    )

    # Section 1 - Current psychiatric symptoms

    death_self_harm_ideation = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Ideação de morte ou autolesão",
    )

    self_harm = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Automutilação",
    )

    perception_thought_changes = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Alterações da percepção ou pensamento",
    )

    intense_anxiety_fear = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Ansiedade ou medo intenso",
    )

    depressed_mood_withdrawal = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Humor deprimido ou retraimento",
    )

    aggressiveness_impulsivity = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Agressividade ou impulsividade",
    )

    # Section 2 - Violence and protection

    neglect = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Negligência",
    )

    physical_psychological_violence = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Violência física ou psicológica",
    )

    sexual_abuse = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Abuso sexual",
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

    housing = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Moradia",
    )

    health_school_access = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Acesso à saúde e escola",
    )

    # Section 4 - Functional impairment

    school_functioning = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Escola",
    )

    development = models.IntegerField(
        choices=RiskScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Desenvolvimento",
    )

    # Section 5 - Protection network

    protective_caregiver = models.IntegerField(
        choices=ProtectionScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Responsável protetivo",
    )

    school_support = models.IntegerField(
        choices=ProtectionScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Escola",
    )

    professional_follow_up = models.IntegerField(
        choices=ProtectionScale.choices,
        validators=ORDINAL_VALIDATORS,
        verbose_name="Acompanhamento profissional",
    )

    RISK_FIELDS = (
        "death_self_harm_ideation",
        "self_harm",
        "perception_thought_changes",
        "intense_anxiety_fear",
        "depressed_mood_withdrawal",
        "aggressiveness_impulsivity",
        "neglect",
        "physical_psychological_violence",
        "sexual_abuse",
        "community_violence_exposure",
        "family_income",
        "housing",
        "health_school_access",
        "school_functioning",
        "development",
    )

    PROTECTION_FIELDS = (
        "protective_caregiver",
        "school_support",
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
        return f"IarvChild #{self.pk}"

    class Meta:
        verbose_name = "IARV Infantil"
        verbose_name_plural = "IARV Infantis"
