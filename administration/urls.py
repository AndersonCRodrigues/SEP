from django.urls import path

from . import views

app_name = "administration"

urlpatterns = [
    path("", views.AdministrativeHomeView.as_view(), name="home"),
    path("painel/", views.PainelAdministracaoView.as_view(), name="painel"),
    path("cadastrar/", views.cadastrar_administrativo, name="cadastrar"),
    path("perfil/", views.PerfilAdministrativoView.as_view(), name="perfil"),
    path(
        "cadastrar-paciente/",
        views.PatientRegistrationStartView.as_view(),
        name="cadastrar_paciente",
    ),
    path(
        "cadastrar-paciente/<slug:step>/",
        views.PatientRegistrationStepView.as_view(),
        name="cadastrar_paciente_etapa",
    ),
    path("pacientes/", views.PatientsView.as_view(), name="pacientes"),
    path(
        "pacientes/<int:pk>/cadastro-concluido/",
        views.RegistrationCompletedView.as_view(),
        name="cadastro_concluido",
    ),
    path("agenda/", views.ScheduleView.as_view(), name="agenda"),
    path("salas/", views.RoomsView.as_view(), name="salas"),
    path("declaracoes/", views.DeclarationsView.as_view(), name="declaracoes"),
    path("atestados/", views.CertificatesView.as_view(), name="atestados"),
    path(
        "atestados/atendimentos/",
        views.CertificateAppointmentsView.as_view(),
        name="atestados_atendimentos",
    ),
]
