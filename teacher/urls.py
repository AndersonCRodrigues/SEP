from django.urls import path
from . import views

app_name = "teacher"

urlpatterns = [
    path("", views.HomeProfessorView.as_view(), name="home"),
    # COMENTADO a pedido do front (validação de 12/09) -- ver nota em views.py
    # path("painel/", views.PainelProfessorView.as_view(), name="painel"),
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
    # Card: Presença e feedback
    path("presenca/", views.PresencaFeedbackView.as_view(), name="presenca"),
    path(
        "presenca/marcar/<int:aluno_id>/",
        views.marcar_presenca,
        name="marcar_presenca",
    ),
    path(
        "presenca/avaliar/<int:aluno_id>/",
        views.registrar_feedback,
        name="registrar_feedback",
    ),
    # Card: Definição de realização de triagem
    path("triagens/", views.TriagensPendentesView.as_view(), name="triagens"),
    path(
        "triagens/<int:patient_id>/",
        views.DefinirTriagemView.as_view(),
        name="triagem_definir",
    ),
]