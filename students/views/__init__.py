from .access import StudentOnly
from .account import (
    MeuProfessorView,
    PainelEstudanteView,
    PerfilAlunoView,
    cadastrar_aluno,
)
from .feedbacks import StudentFeedbacksView
from .home import HomeEstudanteView
from .records import StudentRecordsView
from .referrals import StudentReferralsView
from .triages import StudentTriagesView, TriageCompletedView

__all__ = [
    "HomeEstudanteView",
    "MeuProfessorView",
    "PainelEstudanteView",
    "PerfilAlunoView",
    "StudentFeedbacksView",
    "StudentOnly",
    "StudentRecordsView",
    "StudentReferralsView",
    "StudentTriagesView",
    "TriageCompletedView",
    "cadastrar_aluno",
]
