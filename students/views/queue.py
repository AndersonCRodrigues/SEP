from patient.models import Patient


def waiting_patients():
    return Patient.objects.awaiting_triage().order_by("created_at")
