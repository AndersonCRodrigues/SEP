from django.urls import path
from . import views

app_name = "students"

urlpatterns = [
    path("", views.HomeEstudanteView.as_view(), name="home"),
    path("painel/", views.PainelEstudanteView.as_view(), name="painel"),
    path("triagens/", views.TriagemAlunoView.as_view(), name="triagens"),
    path("feedbacks/", views.FeedbacksAlunoView.as_view(), name="feedbacks"),
    path("encaminhamentos/", views.EncaminhamentosAlunoView.as_view(), name="encaminhamentos"),
    path("cadastrar/", views.cadastrar_aluno, name="cadastrar"),
    path("perfil/", views.PerfilAlunoView.as_view(), name="perfil"),
    path("meu-professor/", views.MeuProfessorView.as_view(), name="meu_professor"),
]
