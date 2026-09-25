from .account import (
    PainelAdministracaoView,
    PerfilAdministrativoView,
    cadastrar_administrativo,
)
from .certificates import CertificateAppointmentsView, CertificatesView
from .declarations import DeclarationsView
from .home import AdministrativeHomeView
from .patients import (
    PatientRegistrationStartView,
    PatientRegistrationStepView,
    PatientsView,
    RegistrationCompletedView,
)
from .rooms import RoomsView
from .schedule import ScheduleView

__all__ = [
    "AdministrativeHomeView",
    "CertificateAppointmentsView",
    "CertificatesView",
    "DeclarationsView",
    "PainelAdministracaoView",
    "PatientRegistrationStartView",
    "PatientRegistrationStepView",
    "PatientsView",
    "PerfilAdministrativoView",
    "RegistrationCompletedView",
    "RoomsView",
    "ScheduleView",
    "cadastrar_administrativo",
]
