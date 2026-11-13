from .appointments import AppointmentRequestView, PatientAppointmentsView
from .contact import PatientContactView
from .history import PatientHistoryView, PatientSessionDetailView
from .home import PatientHomeView
from .profile import PatientProfileView

from .triages import PatientTriageDetailView, PatientTriagesView
from .first_access import PatientFirstAccessView

__all__ = [
    "AppointmentRequestView",
    "PatientAppointmentsView",
    "PatientContactView",
    "PatientHistoryView",
    "PatientHomeView",
    "PatientSessionDetailView",
    "PatientTriageDetailView",
    "PatientTriagesView",
    "PatientProfileView",
    "PatientFirstAccessView",
]
