from patient.models import Patient

WAITING = ("", Patient.FlowStatus.AWAITING_TRIAGE)


def waiting_patients():
    return Patient.objects.filter(flow_status__in=WAITING).order_by("created_at")
