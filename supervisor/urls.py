from django.urls import path
from . import views

app_name = "supervisor"

urlpatterns = [
    path("", views.CoordinatorHomeView.as_view(), name="home"),
    path("perfil/", views.PerfilSupervisorView.as_view(), name="perfil"),
    path("painel/", views.PainelSupervisorView.as_view(), name="painel"),
    path("usuarios/", views.CoordinatorTeachersView.as_view(), name="listar_usuarios"),
    path("register/", views.cadastrar_supervisor, name="register"),
    path("areas/", views.ListaAreasView.as_view(), name="areas"),
    path("areas/nova/", views.CriarAreaView.as_view(), name="area_criar"),
    path("areas/<int:pk>/editar/", views.EditarAreaView.as_view(), name="area_editar"),
    path("professores/", views.CoordinatorTeachersView.as_view(), name="professores"),
    path(
        "professores/<int:pk>/",
        views.CoordinatorTeacherDetailView.as_view(),
        name="professor_detalhe",
    ),
    path("alunos/", views.CoordinatorStudentsView.as_view(), name="alunos"),
    path(
        "alunos/<int:pk>/",
        views.CoordinatorStudentDetailView.as_view(),
        name="aluno_detalhe",
    ),
    path("triagens/", views.CoordinatorTriagesView.as_view(), name="triagens"),
    path(
        "triagens/<int:pk>/",
        views.CoordinatorTriageDetailView.as_view(),
        name="triagem_detalhe",
    ),
    path(
        "encaminhamentos/",
        views.CoordinatorReferralsView.as_view(),
        name="encaminhamentos",
    ),
    path(
        "encaminhamentos/<int:pk>/",
        views.CoordinatorReferralsView.as_view(),
        name="encaminhar",
    ),
    path("feedbacks/", views.CoordinatorFeedbacksView.as_view(), name="feedbacks"),
    path(
        "orientacao/",
        views.PainelOrientacaoSupervisorView.as_view(),
        name="orientacao",
    ),
]
