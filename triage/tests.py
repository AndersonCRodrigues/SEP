from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from patient.models import Patient
from students.models import Aluno

from .forms import (
    IarvAdultForm,
    IarvAdolescentForm,
    IarvChildForm,
)
from .models import (
    IarvAdult,
    IarvAdolescent,
    IarvChild,
    TriageRecord,
)
from .views import get_iarv_form_class


class IarvCalculationTests(SimpleTestCase):
    def test_adult_risk_score_subtracts_protection(self):
        iarv = IarvAdult(
            suicidal_ideation=3,
            self_harm=2,
            psychosis_delusions_hallucinations=1,
            anxiety_panic=2,
            depressed_mood=2,
            alcohol_drug_abuse=1,
            domestic_violence=1,
            homelessness=0,
            income_and_work=1,
            healthcare_access=1,
            housing_conditions=1,
            daily_living_activities=1,
            work_or_studies=1,
            family_relationships=1,
            family_support=3,
            community_support=2,
            ongoing_treatment=1,
        )

        self.assertEqual(iarv.calculate_risk_sum(), 18)
        self.assertEqual(iarv.calculate_protection_sum(), 6)
        self.assertEqual(iarv.calculate_score(), 12)

    def test_adolescent_risk_score_subtracts_protection(self):
        iarv = IarvAdolescent(
            suicidal_ideation=2,
            self_harm_behavior=1,
            perception_thought_changes=1,
            anxiety_panic=2,
            depressed_mood=2,
            impulsivity_aggressiveness=1,
            alcohol_drug_use=1,
            domestic_violence=1,
            physical_sexual_abuse=0,
            bullying_school_violence=1,
            community_violence_exposure=1,
            family_income=1,
            housing_conditions=1,
            health_school_network_access=1,
            school_functioning=1,
            family_relationships=1,
            social_life=1,
            family_caregiver_support=3,
            school_community_support=2,
            professional_follow_up=2,
        )

        self.assertEqual(iarv.calculate_risk_sum(), 19)
        self.assertEqual(iarv.calculate_protection_sum(), 7)
        self.assertEqual(iarv.calculate_score(), 12)

    def test_child_risk_score_subtracts_protection(self):
        iarv = IarvChild(
            death_self_harm_ideation=1,
            self_harm=1,
            perception_thought_changes=1,
            intense_anxiety_fear=2,
            depressed_mood_withdrawal=2,
            aggressiveness_impulsivity=1,
            neglect=1,
            physical_psychological_violence=1,
            sexual_abuse=0,
            community_violence_exposure=1,
            family_income=1,
            housing=1,
            health_school_access=1,
            school_functioning=1,
            development=1,
            protective_caregiver=3,
            school_support=3,
            professional_follow_up=2,
        )

        self.assertEqual(iarv.calculate_risk_sum(), 16)
        self.assertEqual(iarv.calculate_protection_sum(), 8)
        self.assertEqual(iarv.calculate_score(), 8)

    def test_adult_low_classification(self):
        iarv = self._create_adult_with_score(5)

        self.assertEqual(
            iarv.get_classification(),
            "LOW",
        )

    def test_adult_medium_classification(self):
        iarv = self._create_adult_with_score(6)

        self.assertEqual(
            iarv.get_classification(),
            "MEDIUM",
        )

    def test_adult_high_classification(self):
        iarv = self._create_adult_with_score(12)

        self.assertEqual(
            iarv.get_classification(),
            "HIGH",
        )

    def test_adult_maximum_classification(self):
        iarv = self._create_adult_with_score(20)

        self.assertEqual(
            iarv.get_classification(),
            "MAXIMUM",
        )

    def test_adult_elevated_protection_classification(self):
        iarv = self._create_adult_with_score(-1)

        self.assertEqual(
            iarv.get_classification(),
            "ELEVATED_PROTECTION",
        )

    def _create_adult_with_score(self, target_score):
        risk_values = [0] * 14
        protection_values = [0] * 3

        if target_score >= 0:
            remaining = target_score

            for index in range(len(risk_values)):
                value = min(remaining, 3)
                risk_values[index] = value
                remaining -= value

                if remaining == 0:
                    break

        else:
            protection_values[0] = abs(target_score)

        return IarvAdult(
            suicidal_ideation=risk_values[0],
            self_harm=risk_values[1],
            psychosis_delusions_hallucinations=risk_values[2],
            anxiety_panic=risk_values[3],
            depressed_mood=risk_values[4],
            alcohol_drug_abuse=risk_values[5],
            domestic_violence=risk_values[6],
            homelessness=risk_values[7],
            income_and_work=risk_values[8],
            healthcare_access=risk_values[9],
            housing_conditions=risk_values[10],
            daily_living_activities=risk_values[11],
            work_or_studies=risk_values[12],
            family_relationships=risk_values[13],
            family_support=protection_values[0],
            community_support=protection_values[1],
            ongoing_treatment=protection_values[2],
        )

    def test_adolescent_classification_limits(self):
        iarv = IarvAdolescent()

        iarv.calculate_score = lambda: -1
        self.assertEqual(
            iarv.get_classification(),
            "ELEVATED_PROTECTION",
        )

        iarv.calculate_score = lambda: 4
        self.assertEqual(iarv.get_classification(), "LOW")

        iarv.calculate_score = lambda: 5
        self.assertEqual(iarv.get_classification(), "MEDIUM")

        iarv.calculate_score = lambda: 10
        self.assertEqual(iarv.get_classification(), "HIGH")

        iarv.calculate_score = lambda: 18
        self.assertEqual(iarv.get_classification(), "MAXIMUM")

    def test_child_classification_limits(self):
        iarv = IarvChild()

        iarv.calculate_score = lambda: -1
        self.assertEqual(
            iarv.get_classification(),
            "ELEVATED_PROTECTION",
        )

        iarv.calculate_score = lambda: 4
        self.assertEqual(iarv.get_classification(), "LOW")

        iarv.calculate_score = lambda: 5
        self.assertEqual(iarv.get_classification(), "MEDIUM")

        iarv.calculate_score = lambda: 10
        self.assertEqual(iarv.get_classification(), "HIGH")

        iarv.calculate_score = lambda: 18
        self.assertEqual(iarv.get_classification(), "MAXIMUM")

class TriageRecordRiskTests(SimpleTestCase):
    def test_calculate_total_risk_uses_related_iarv(self):
        triage_record = TriageRecord()

        iarv = IarvAdult()
        iarv.calculate_score = lambda: 12

        triage_record.get_iarv = lambda: iarv

        self.assertEqual(
            triage_record.calculate_total_risk(),
            12,
        )

    def test_calculate_total_risk_returns_none_without_iarv(self):
        triage_record = TriageRecord()

        triage_record.get_iarv = lambda: None

        self.assertIsNone(
            triage_record.calculate_total_risk()
        )

    def test_get_risk_classification_uses_related_iarv(self):
        triage_record = TriageRecord()

        iarv = IarvAdult()
        iarv.calculate_score = lambda: 20

        triage_record.get_iarv = lambda: iarv

        self.assertEqual(
            triage_record.get_risk_classification(),
            "MAXIMUM",
        )


def test_get_risk_classification_returns_none_without_iarv(self):
    triage_record = TriageRecord()

    triage_record.get_iarv = lambda: None

    self.assertIsNone(
        triage_record.get_risk_classification()
    )

class IarvRoutingTests(SimpleTestCase):
    def test_child_form_is_selected_for_age_under_13(self):
        patient = type(
            "PatientStub",
            (),
            {"current_age": 12},
        )()

        self.assertIs(
            get_iarv_form_class(patient),
            IarvChildForm,
        )

    def test_adolescent_form_is_selected_for_age_13(self):
        patient = type(
            "PatientStub",
            (),
            {"current_age": 13},
        )()

        self.assertIs(
            get_iarv_form_class(patient),
            IarvAdolescentForm,
        )

    def test_adolescent_form_is_selected_for_age_17(self):
        patient = type(
            "PatientStub",
            (),
            {"current_age": 17},
        )()

        self.assertIs(
            get_iarv_form_class(patient),
            IarvAdolescentForm,
        )

    def test_adult_form_is_selected_for_age_over_17(self):
        patient = type(
            "PatientStub",
            (),
            {"current_age": 18},
        )()

        self.assertIs(
            get_iarv_form_class(patient),
            IarvAdultForm,
        )

    def test_patient_without_birth_date_cannot_select_form(self):
        patient = type(
            "PatientStub",
            (),
            {"current_age": None},
        )()

        with self.assertRaisesMessage(
            ValidationError,
            "A data de nascimento do paciente é obrigatória para selecionar o questionário IARV.",
        ):
            get_iarv_form_class(patient)

class TriageRecordSaveTests(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(
            email="patient.triage@test.com",
            nome_completo="Paciente Teste",
            cpf="12345678909",
            telefone="21999999999",
        )

        self.student = Aluno.objects.create(
            email="student.triage@test.com",
            nome_completo="Aluno Teste",
            cpf="52998224725",
            telefone="21888888888",
        )

    def test_save_sets_patient_flow_status_to_in_triage_on_creation(self):
        self.assertEqual(
            self.patient.flow_status,
            "",
        )

        TriageRecord.objects.create(
            patient=self.patient,
            student_author=self.student,
            chief_complaint="Queixa clínica de teste.",
        )

        self.patient.refresh_from_db()

        self.assertEqual(
            self.patient.flow_status,
            Patient.FlowStatus.IN_TRIAGE,
        )

    def test_subsequent_save_does_not_change_patient_flow_status(self):
        triage_record = TriageRecord.objects.create(
            patient=self.patient,
            student_author=self.student,
            chief_complaint="Queixa clínica de teste.",
        )

        self.patient.refresh_from_db()

        self.assertEqual(
            self.patient.flow_status,
            Patient.FlowStatus.IN_TRIAGE,
        )

        # Simula uma alteração posterior no status do paciente.
        self.patient.flow_status = ""
        self.patient.save(update_fields=["flow_status"])

        triage_record.summary_and_impressions = "Atualização da triagem."
        triage_record.save(
            update_fields=["summary_and_impressions"]
        )

        self.patient.refresh_from_db()

        self.assertEqual(
            self.patient.flow_status,
            "",
        )