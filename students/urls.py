from django.urls import path

from . import views

app_name = "students"

urlpatterns = [
    path("", views.HomeEstudanteView.as_view(), name="home"),
    path("painel/", views.PainelEstudanteView.as_view(), name="painel"),
    path("cadastrar/", views.cadastrar_aluno, name="cadastrar"),
    path("perfil/", views.PerfilAlunoView.as_view(), name="perfil"),
    path("meu-professor/", views.MeuProfessorView.as_view(), name="meu_professor"),
    path("prontuarios/", views.StudentRecordsView.as_view(), name="prontuarios"),
    path("triagens/", views.StudentTriagesView.as_view(), name="triagens"),
    path(
        "triagens/<int:pk>/concluida/",
        views.TriageCompletedView.as_view(),
        name="triagem_concluida",
    ),
    path(
        "encaminhamentos/",
        views.StudentReferralsView.as_view(),
        name="encaminhamentos",
    ),
    path("feedbacks/", views.StudentFeedbacksView.as_view(), name="feedbacks"),
    # Telas do front, em rota própria enquanto o desenho não é portado para as
    # telas acima, que já têm consulta e recorte por visibilidade.
    path("area/triagens/", views.TriagemAlunoView.as_view(), name="area_triagens"),
    path(
        "area/encaminhamentos/",
        views.EncaminhamentosAlunoView.as_view(),
        name="area_encaminhamentos",
    ),
    path("area/feedbacks/", views.FeedbacksAlunoView.as_view(), name="area_feedbacks"),
]
