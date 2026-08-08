from django.test import TestCase
from audit.models import AuditLog
from patient.models import Patient
from students.models import Aluno
from triage.models import TriageRecord
from django.db import connection


class AuditSignalTests(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(
            email="patient.audit@test.com",
            nome_completo="Paciente Teste",
            cpf="12345678909",
            telefone="21999999999",
        )

        self.student = Aluno.objects.create(
            email="student.audit@test.com",
            nome_completo="Aluno Teste",
            cpf="52998224725",
            telefone="21888888888",
        )

    def test_patient_creation_generates_audit_log(self):
        self.assertTrue(
            AuditLog.objects.filter(
                model_name="Patient",
                object_id=str(self.patient.pk),
                action=AuditLog.Action.CREATE,
            ).exists()
        )

    def test_patient_update_generates_audit_log(self):
        self.patient.flow_status = Patient.FlowStatus.IN_TRIAGE
        self.patient.save(update_fields=["flow_status"])

        audit_log = AuditLog.objects.filter(
            model_name="Patient",
            object_id=str(self.patient.pk),
            action=AuditLog.Action.UPDATE,
        ).latest("created_at")

        self.assertEqual(
            audit_log.changes,
            {
                "flow_status": {
                    "changed": True,
                }
            },
        )

    def test_patient_delete_generates_audit_log(self):
        patient_id = self.patient.pk

        self.patient.delete()

        self.assertTrue(
            AuditLog.objects.filter(
                model_name="Patient",
                object_id=str(patient_id),
                action=AuditLog.Action.DELETE,
            ).exists()
        )

    def test_triage_creation_generates_audit_log(self):
        triage_record = TriageRecord.objects.create(
            patient=self.patient,
            student_author=self.student,
            chief_complaint="Conteúdo clínico de teste.",
        )

        self.assertTrue(
            AuditLog.objects.filter(
                model_name="TriageRecord",
                object_id=str(triage_record.pk),
                action=AuditLog.Action.CREATE,
            ).exists()
        )

    def test_triage_update_generates_audit_log_without_plaintext(self):
        triage_record = TriageRecord.objects.create(
            patient=self.patient,
            student_author=self.student,
            chief_complaint="Conteúdo clínico inicial.",
        )

        new_complaint = "Novo conteúdo clínico sigiloso."

        triage_record.chief_complaint = new_complaint
        triage_record.save(update_fields=["chief_complaint"])

        audit_log = AuditLog.objects.filter(
            model_name="TriageRecord",
            object_id=str(triage_record.pk),
            action=AuditLog.Action.UPDATE,
        ).latest("created_at")

        self.assertEqual(
            audit_log.changes,
            {
                "chief_complaint": {
                    "changed": True,
                }
            },
        )

        self.assertNotIn(
            new_complaint,
            str(audit_log.changes),
        )

    def test_triage_delete_generates_audit_log(self):
        triage_record = TriageRecord.objects.create(
            patient=self.patient,
            student_author=self.student,
            chief_complaint="Conteúdo clínico de teste.",
        )

        triage_id = triage_record.pk

        triage_record.delete()

        self.assertTrue(
            AuditLog.objects.filter(
                model_name="TriageRecord",
                object_id=str(triage_id),
                action=AuditLog.Action.DELETE,
            ).exists()
        )
    def test_sensitive_triage_field_is_encrypted_in_database(self):
        plaintext = "Informação clínica extremamente sigilosa."

        triage_record = TriageRecord.objects.create(
            patient=self.patient,
            student_author=self.student,
            chief_complaint=plaintext,
        )

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT chief_complaint
                FROM triage_triagerecord
                WHERE id = %s
                """,
                [triage_record.pk],
            )

            stored_value = cursor.fetchone()[0]

        self.assertNotEqual(
            stored_value,
            plaintext,
        )

        triage_record.refresh_from_db()

        self.assertEqual(
            triage_record.chief_complaint,
            plaintext,
        )