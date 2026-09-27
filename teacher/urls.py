from django.urls import path

from . import views

app_name = "teacher"

urlpatterns = [
    path("", views.HomeProfessorView.as_view(), name="home"),
    path("cadastrar/", views.cadastrar_professor, name="cadastrar"),
    path("perfil/", views.PerfilProfessorView.as_view(), name="perfil"),
    path("vincular-aluno/", views.vincular_aluno, name="vincular_aluno"),
    path("lancar-horas/", views.lancar_horas, name="lancar_horas"),
    # Card: Alunos sob orientação
    path("alunos/", views.AlunosOrientacaoView.as_view(), name="alunos"),
    path("alunos/<int:pk>/", views.AlunoDetalheView.as_view(), name="aluno_detalhe"),
    # Card: Prontuários
    path("prontuarios/", views.ProntuariosView.as_view(), name="prontuarios"),
    path(
        "prontuarios/<int:pk>/",
        views.ProntuarioDetalheView.as_view(),
        name="prontuario_detalhe",
    ),
    # Card: Presença
    path("presenca/", views.PresencaView.as_view(), name="presenca"),
    path(
        "presenca/marcar/<int:aluno_id>/",
        views.marcar_presenca,
        name="marcar_presenca",
    ),
    # Card: Avaliações
    path("avaliacoes/", views.AvaliacoesView.as_view(), name="avaliacoes"),
    path(
        "avaliacoes/<int:aluno_id>/",
        views.registrar_feedback,
        name="registrar_feedback",
    ),
    # Card: Encaminhar
    path("encaminhamentos/", views.EncaminharView.as_view(), name="encaminhamentos"),
    path(
        "encaminhamentos/<int:pk>/",
        views.EncaminharView.as_view(),
        name="encaminhar",
    ),
]
