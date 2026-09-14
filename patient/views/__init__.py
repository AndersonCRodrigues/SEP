from .appointments import AppointmentRequestView, PatientAppointmentsView
from .contact import PatientContactView
from .history import PatientHistoryView, PatientSessionDetailView
from .home import PatientHomeView
from .profile import EditarDadosPacienteView, enviar_email
from .triages import PatientTriageDetailView, PatientTriagesView

__all__ = [
    "AppointmentRequestView",
    "EditarDadosPacienteView",
    "PatientAppointmentsView",
    "PatientContactView",
    "PatientHistoryView",
    "PatientHomeView",
    "PatientSessionDetailView",
    "PatientTriageDetailView",
    "PatientTriagesView",
    "enviar_email",
]
