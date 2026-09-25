from .access import StudentOnly
from .account import (
    MeuProfessorView,
    PainelEstudanteView,
    PerfilAlunoView,
    cadastrar_aluno,
)
from .feedbacks import StudentFeedbacksView
from .front import (
    EncaminhamentosAlunoView,
    FeedbacksAlunoView,
    TriagemAlunoView,
)
from .home import HomeEstudanteView
from .records import StudentRecordsView
from .referrals import StudentReferralsView
from .triages import StudentTriagesView, TriageCompletedView

__all__ = [
    "EncaminhamentosAlunoView",
    "FeedbacksAlunoView",
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
    "TriagemAlunoView",
    "cadastrar_aluno",
]
