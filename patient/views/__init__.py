from .appointments import AppointmentRequestView, PatientAppointmentsView
from .contact import PatientContactView
from .history import PatientHistoryView, PatientSessionDetailView
from .home import PatientHomeView
from .profile import enviar_email
from .triages import PatientTriageDetailView, PatientTriagesView

__all__ = [
    "AppointmentRequestView",
    "PatientAppointmentsView",
    "PatientContactView",
    "PatientHistoryView",
    "PatientHomeView",
    "PatientSessionDetailView",
    "PatientTriageDetailView",
    "PatientTriagesView",
    "enviar_email",
]
