from .access import CoordinatorOnly
from .account import (
    PainelSupervisorView,
    PerfilSupervisorView,
    cadastrar_supervisor,
    usuarios_alunos_e_professores,
)
from .areas import CriarAreaView, EditarAreaView, ListaAreasView
from .feedbacks import CoordinatorFeedbacksView
from .home import CoordinatorHomeView
from .orientation import PainelOrientacaoSupervisorView
from .referrals import CoordinatorReferralsView
from .students import CoordinatorStudentDetailView, CoordinatorStudentsView
from .teachers import CoordinatorTeacherDetailView, CoordinatorTeachersView
from .triages import CoordinatorTriageDetailView, CoordinatorTriagesView

__all__ = [
    "CoordinatorFeedbacksView",
    "CoordinatorHomeView",
    "CoordinatorOnly",
    "CoordinatorReferralsView",
    "CoordinatorStudentDetailView",
    "CoordinatorStudentsView",
    "CoordinatorTeacherDetailView",
    "CoordinatorTeachersView",
    "CoordinatorTriageDetailView",
    "CoordinatorTriagesView",
    "CriarAreaView",
    "EditarAreaView",
    "ListaAreasView",
    "PainelOrientacaoSupervisorView",
    "PainelSupervisorView",
    "PerfilSupervisorView",
    "cadastrar_supervisor",
    "usuarios_alunos_e_professores",
]
